import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MemoryConfig:
    window_messages: int
    window_time_span: int
    summarization_trigger_type: Optional[str]
    summarization_trigger_value: Optional[int]
    summarization_threshold: Optional[float]
    lru_cache_max_threads: int
    lru_cache_context_length: int

@dataclass
class StyleConfig:
    communication: List[str]
    analysis: List[str]

@dataclass
class ProtocolConfig:
    id: str
    agent_definition: 'AgentDefinitionConfig'
    input_handling: 'InputHandlingConfig'
    output_handling: 'OutputHandlingConfig'

@dataclass
class AgentDefinitionConfig:
    objectives: 'ObjectivesConfig'
    style: StyleConfig
    constraints: 'ConstraintsConfig'
    behavior: 'BehaviorConfig'
    counterparty_perception: 'CounterpartyPerceptionConfig'

@dataclass
class ObjectivesConfig:
    primary: str
    secondary: List[str]
    metrics: List[str]

@dataclass
class ConstraintsConfig:
    operational: List[str]
    technical: List[str]

@dataclass
class BehaviorConfig:
    core_function: str
    methodology: List[str]

@dataclass
class CounterpartyPerceptionConfig:
    assumptions: List[str]
    adaptation_strategies: List[str]

@dataclass
class InputHandlingConfig:
    message_format_schema: str
    analysis_points: List[str]
    history_processing: List[str]

@dataclass
class OutputHandlingConfig:
    format: str
    style: StyleConfig
    response_schema: str

@dataclass
class ServiceConfig:
    provider: str
    model: str
    api_version: str

@dataclass
class MomentumMessage:
    role_type: str
    content: str
    position: int

@dataclass
class MomentumSequence:
    id: str
    type: str
    protocol_ref: str
    temperature: float
    messages: List[MomentumMessage]

@dataclass
class AgentConfig:
    name: str
    type: str
    category: str
    version: str
    response_interval: int
    response_interval_unit: str
    memory: MemoryConfig
    protocols: List[ProtocolConfig]
    momentum_sequences: List[MomentumSequence]
    service: ServiceConfig

def parse_style(element: ET.Element) -> StyleConfig:
    """Parse style configuration"""
    return StyleConfig(
        communication=[aspect.text for aspect in element.find('communication').findall('aspect')],
        analysis=[aspect.text for aspect in element.find('analysis').findall('aspect')]
    )

def parse_memory_config(element: ET.Element) -> MemoryConfig:
    """Parse memory configuration"""
    window = element.find('window')
    summarization = element.find('summarization')
    history = element.find('history')
    lru_cache = history.find('lru_cache')
    threads = lru_cache.find('threads')
    context = threads.find('context')

    return MemoryConfig(
        window_messages=int(window.find('messages').text),
        window_time_span=int(window.find('time_span').text),
        summarization_trigger_type=summarization.find('trigger').get('type') if summarization is not None else None,
        summarization_trigger_value=int(summarization.find('trigger').text) if summarization is not None else None,
        summarization_threshold=float(summarization.find('threshold').text) if summarization is not None else None,
        lru_cache_max_threads=int(threads.get('max_count')),
        lru_cache_context_length=int(context.get('length'))
    )

def parse_protocol(element: ET.Element) -> ProtocolConfig:
    """Parse protocol configuration"""
    agent_def = element.find('agent_definition')
    
    objectives = agent_def.find('objectives')
    style = parse_style(agent_def.find('style'))
    constraints = agent_def.find('constraints')
    behavior = agent_def.find('behavior')
    perception = agent_def.find('counterparty_perception')

    input_handling = element.find('input_handling')
    output_handling = element.find('output_handling')

    return ProtocolConfig(
        id=element.get('id'),
        agent_definition=AgentDefinitionConfig(
            objectives=ObjectivesConfig(
                primary=objectives.find('primary').text,
                secondary=[s.text for s in objectives.findall('secondary')],
                metrics=[m.text for m in objectives.find('metrics').findall('metric')]
            ),
            style=style,
            constraints=ConstraintsConfig(
                operational=[o.text for o in constraints.findall('operational')],
                technical=[t.text for t in constraints.findall('technical')]
            ),
            behavior=BehaviorConfig(
                core_function=behavior.find('core_function').text,
                methodology=[s.text for s in behavior.find('methodology').findall('step')]
            ),
            counterparty_perception=CounterpartyPerceptionConfig(
                assumptions=[a.text for a in perception.findall('assumption')],
                adaptation_strategies=[s.text for s in perception.findall('adaptation_strategy')]
            )
        ),
        input_handling=InputHandlingConfig(
            message_format_schema=input_handling.find('message_format/schema').text,
            analysis_points=[p.text for p in input_handling.find('analysis_points').findall('point')],
            history_processing=[i.text for i in input_handling.find('history_processing').findall('instruction')]
        ),
        output_handling=OutputHandlingConfig(
            format=output_handling.find('format').text,
            style=parse_style(output_handling.find('style')),
            response_schema=output_handling.find('response_schema').text
        )
    )

def parse_momentum_sequence(element: ET.Element) -> MomentumSequence:
    """Parse momentum sequence from XML element"""
    messages = []
    for msg in element.findall('message'):
        messages.append(MomentumMessage(
            role_type=msg.find('role').get('type'),
            content=msg.find('content').text if msg.find('content') is not None else '',
            position=int(msg.get('position'))
        ))
    
    return MomentumSequence(
        id=element.get('id'),
        type=element.get('type'),
        protocol_ref=element.get('protocol_ref'),
        temperature=float(element.get('temperature')),
        messages=messages
    )

def load_agent_config(xml_path: str) -> AgentConfig:
    """Load agent configuration from XML file"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Parse metadata
    metadata = root.find('metadata')
    name = metadata.find('name').text
    type_elem = metadata.find('type')
    type_text = type_elem.text
    category = type_elem.get('category')
    version = metadata.find('version').text
    
    timing = metadata.find('timing')
    response_interval = int(timing.find('response_interval').text)
    response_interval_unit = timing.find('response_interval').get('unit')

    service = metadata.find('service')
    provider = service.find('provider').text
    model = service.find('model').text
    api_version = service.find('api_version').text

    # Parse memory config
    memory = parse_memory_config(root.find('memory'))

    # Parse protocols
    protocols = [parse_protocol(p) for p in root.find('protocols').findall('protocol')]

    # Parse momentum sequences
    momentum = root.find('momentum')
    sequences = []
    for seq in momentum.findall('sequence'):
        sequences.append(parse_momentum_sequence(seq))

    return AgentConfig(
        name=name,
        type=type_text,
        category=category,
        version=version,
        response_interval=response_interval,
        response_interval_unit=response_interval_unit,
        memory=memory,
        protocols=protocols,
        momentum_sequences=sequences,
        service=ServiceConfig(
            provider=provider,
            model=model,
            api_version=api_version
        )
    ) 
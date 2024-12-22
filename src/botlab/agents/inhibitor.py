from typing import Dict, Optional
import logging
from .filter import Filter
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class InhibitorFilter(Filter):
    """
    Inhibitor that filters messages based on conversation context and agent role.
    Makes binary allow/block decisions using status codes.
    """
    
    def __init__(self, config, speaker_prompt: str = ""):
        super().__init__(config)
        self.speaker_prompt = speaker_prompt
        
    def get_metadata(self) -> Dict:
        """Get agent metadata"""
        return {
            'name': self.config.name,
            'type': self.config.type,
            'category': self.config.category,
            'version': self.config.version
        }
        
    async def _filter_message(self, message: Dict) -> Optional[Dict]:
        """Determine if message should be allowed or blocked"""
        try:
            logger.debug("Starting inhibitor analysis")
            # Get system prompt and inject speaker context
            init_sequence = self.config.get_momentum_sequence('initialization')
            system_msg = ""
            for msg in init_sequence:
                if msg.role_type == 'system':
                    system_msg = msg.content.replace('[SPEAKER_PROMPT]', self.speaker_prompt)
                    break

            logger.debug(f"Analyzing history: {message.get('history_xml', '')[:200]}...")
            # Format analysis request
            history_xml = message.get('history_xml', '')
            analysis_request = f"""
            Analyze this conversation history and determine if a response is appropriate:
            {history_xml}
            """

            # Get LLM analysis
            logger.debug("Calling LLM for inhibition analysis")
            analysis = await self._call_llm(system_msg, analysis_request)
            if not analysis:
                logger.warning("No response from LLM for inhibition analysis")
                return None

            # Parse response
            try:
                xml_start = analysis.find('<message')
                xml_end = analysis.find('</message>') + len('</message>')
                if xml_start == -1 or xml_end == -1:
                    logger.error("Could not find message tags in LLM response")
                    return None
                    
                xml_content = analysis[xml_start:xml_end]
                message = ET.fromstring(xml_content)
                
                code = message.get('code', '500')
                reason = message.text if message.text else "No reason provided"
                
                logger.info(f"Inhibitor decision: code={code}, reason={reason}")
                return {
                    'code': code,
                    'reason': reason
                }
                
            except ET.ParseError as e:
                logger.error(f"Failed to parse LLM response as XML: {e}")
                return None

        except Exception as e:
            logger.error(f"Error in filter analysis: {str(e)}")
            return None 
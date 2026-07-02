
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from advcms.settings import app_settings

helper_remote_agent = RemoteA2aAgent(
    name="ADVCMS_Helper_Agent",
    description="You are a helper agent for the content management system. Provide a response based on your knowledge and the context provided. You should answer in a concise and clear manner.", 
    agent_card=f"http://{app_settings.HOST}:7007/a2a/helper_agent/"
)

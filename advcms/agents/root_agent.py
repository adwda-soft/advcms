
from collections.abc import AsyncGenerator
from sched import Event

from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search

from google.genai import types
from advcms.settings import app_settings
from advcms.agents.tools.chroma_tool import app_chromaconnector

class ADVCMSRootAgent:

    def __init__(self):
        self.ad_agent = None

        self.ad_agent_runner = None
        self.ad_agent_session = None
        self.ad_agent_session_service = None       
                
        self.AGENT_INSTRUCTION = """
        You are an AI assistant designed to answer user queries.
        Never assume, guess, or make up facts. 
        Whenever a user asks for information, YOU MUST answer to the question by analyses of part after ADVCMSDATA if it exists.
        YOU MUST insert ADVCMSRESULT in front of the final answer.
        Please provide a direct answer without explaining your thinking and reasoning steps
        """
  
    def query_chrome_data(self, username:str, query_txt: str, lookupnum: int):

        return app_chromaconnector.query_chrome_data(username, query_txt, lookupnum)

    async def setup_agent_async(self, username:str):

        if self.ad_agent is None:
            ad_agent_model = app_settings.AGENT_MODEL_FULL_NAME
            if app_settings.AGENT_MODEL_FULL_NAME.startswith("ollama_chat"):
                ad_agent_model = LiteLlm(model=app_settings.AGENT_MODEL_FULL_NAME)

            self.ad_agent = LlmAgent(
                name="ADVCMS_Root_Agent",
                model=ad_agent_model,
                description="You are a personal assistant for the content management system. Provide a response based on your knowledge and the context provided. You should answer in a concise and clear manner.", 
                instruction=self.AGENT_INSTRUCTION
            )
        
        if self.ad_agent_session_service is None:
            self.ad_agent_session_service = InMemorySessionService()
            
        if self.ad_agent_session is None:
            self.ad_agent_session = await self.ad_agent_session_service.create_session(app_name=app_settings.AGENT_APP_NAME, user_id=app_settings.AGENT_USER_ID, session_id=app_settings.AGENT_SESSION_ID)
            
        if self.ad_agent_runner is None:
            self.ad_agent_runner = Runner(agent=self.ad_agent, app_name=app_settings.AGENT_APP_NAME, session_service=self.ad_agent_session_service)

    async def call_agent_async(self, username:str, query: str, searchinposts: bool, lookupnum: int):
        
        try:
            await self.setup_agent_async(username)
            
            response_text = ""
            
            if self.ad_agent_runner is not None:
                
                query_info = query
                if searchinposts:
                    query_result = await self.query_chrome_data(username, query, lookupnum)
                    query_info = f"{query} ADVCMSDATA {query_result}"
                
                print('query_info: ', query_info)
                
                content = types.Content(role='user', parts=[types.Part(text=query_info)])

                events: AsyncGenerator[Event, None] = self.ad_agent_runner.run_async(user_id=app_settings.AGENT_USER_ID, session_id=app_settings.AGENT_SESSION_ID, new_message=content)
                async for event in events:
                    try:
                        if event.is_final_response():
                            if event.content and event.content.parts:
                                for part in event.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        response_text += part.text

                        elif event.content and event.partial:
                            pass
                    except Exception as e:
                        pass

            sub_response_text = response_text.split("ADVCMSRESULT")
            if len(sub_response_text) > 0: 
                response_text = sub_response_text[-1].strip()

            return (1, response_text)

        except Exception as e:

            return (-1, (f"Error during agent execution: {e}"))

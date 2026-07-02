
from binascii import Error
import os
import html2text
from typing import List, Dict, Any
from chromadb import AsyncHttpClient as CRMAsyncHttpClient
from chromadb.config import Settings as CRMSettings
from chromadb.api.types import QueryResult as CRMQueryResult
from chromadb.api.async_api import AsyncCollection as CRMCollection
from advcms.settings import app_settings

class ChromaToolConnector:
    
    def __init__(self): 
        self.persist_directory: str = ""
        self.client : CRMAsyncHttpClient = None
        
    def HtmlToText(self, html: str)->str:
        if not html:
            return ""
        return html2text.html2text(html)
    
    def SetPersistDirectory(self, main_file_path: str):
        self.persist_directory = os.path.join(main_file_path, app_settings.CHROMA_DATA_DIR)
    
    async def setup(self):
        
        os.environ["GEMINI_API_KEY"] = app_settings.GEMINI_API_KEY

        if self.client is None:
            chroma_settings = CRMSettings()
            chroma_settings.persist_directory = self.persist_directory
            chroma_settings.is_persistent = True
            self.client : CRMAsyncHttpClient = await CRMAsyncHttpClient(port=app_settings.CHROMA_PORT, settings=chroma_settings)
    
    async def get_collection(self, username:str) -> CRMCollection:
        
        if self.client is None:
            await self.setup()
        
        collection_name = f"advcms_collection_{username}"
        return await self.client.create_collection(name=collection_name, get_or_create=True)
    
    async def add_data(self, username:str, id: str, doc: str, metadata: Dict[str, str]):
        
        try:
            user_collection = await self.get_collection(username)
            if user_collection is not None:
                await user_collection.add(
                    ids=id,
                    documents=doc,
                    metadatas=metadata
                )      
                #print(f'was called update_data success add for id: {id} and doc: {doc} and metadata: {metadata}')
                
                return 1
            
            return -1  
        except Exception as e:
            return -2      
            
     
    async def update_data(self, username:str, id: str, doc: str, metadata: Dict[str, str]):

        try:
            user_collection : CRMCollection = await self.get_collection(username)
            
            if user_collection is not None:
                
                try:
                    await user_collection.upsert(
                        ids=id,
                        documents=doc,
                        metadatas=metadata
                    )
                    #print(f'was called update_data success update for id: {id} and doc: {doc} and metadata: {metadata}')
                    
                    return 1
                
                except Exception as exc:
                    #print('was called update_data exception during add: ', exc)
                    return -1
                except Error as err:
                    #print('was called update_data exception during add: ', err)
                    return -2
            
            return -1  
        except Exception as e:
            #print('was called update_data exception: ', e)
            return -3      
                         
    async def query_chrome_data(self, username:str, query_txt: str, top_k: int) -> str:

        matched_posts_data = []

        if top_k < 1:
            return ""
        
        if not query_txt or not query_txt.strip():
            return ""
              
        user_collection = await self.get_collection(username)
                
        if user_collection is not None:
            
            query_result : CRMQueryResult = await user_collection.query(
                query_texts=query_txt,
                n_results=top_k
            )

            #print(f'Found Collection for user: {username} with {len(query_result["ids"])} results query_result: ', query_result)

            try:
                matched_posts_data.append("[")
                
                for ids, documents, metadatas in zip(query_result["ids"], query_result["documents"], query_result["metadatas"]):
                    for id, document, metadata in zip(ids, documents, metadatas):
                        
                        if document is None:
                            continue
                                                
                        category = "unknown"
                        if metadata is not None:
                            category = metadata.get("category", "unknown")
                        
                        title = "unknown"
                        if metadata is not None:
                            title = metadata.get("title", "unknown")
                
                        summary = "unknown"
                        if metadata is not None:
                            summary = metadata.get("summary", "unknown")

                        current_match_data = f'id: "{id}", category: "{category}", title: "{title}", summary: "{summary}", post: "{str(document)}"'
                        #print('current_match_data: ', current_match_data)
                        
                        matched_posts_data.append("{")
                        matched_posts_data.append(current_match_data)
                        matched_posts_data.append("},")
                
                matched_posts_data.append("]")
            except Exception as e:
                print('Error processing chroma query results: ', e)
        else:
            print('No collection found for user: ', username)

        return ''.join(matched_posts_data)
    
app_chromaconnector = ChromaToolConnector()
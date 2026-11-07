import json
import time

from servicio.datos.sqlite_store import cosine


class QueryCache:
    def __init__(self,store,ttl_seconds,semantic_threshold):
        self.store=store
        self.ttl=ttl_seconds
        self.threshold=semantic_threshold

    def get(self,project_id,function_name,fingerprint,question,vector):
        for item in self.store.all_cache(project_id,function_name,fingerprint):
            if time.time()-item['created_epoch']>self.ttl:
                continue
            if item['question'].strip().casefold()==question.strip().casefold():
                return json.loads(item['output_json']), 'exacta'
            if cosine(vector,json.loads(item['question_vector']))>=self.threshold:
                return json.loads(item['output_json']), 'semantica'
        return None,'ninguna'

    def put(self,project_id,function_name,fingerprint,question,vector,result):
        self.store.write_cache(project_id,function_name,fingerprint,question,vector,result,time.time())


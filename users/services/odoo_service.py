import json
import requests
from urllib.parse import urljoin

class OdooService:
    def __init__(self, db_url, db_name, email, api_key):
        self.db_url = db_url
        self.db_name = db_name
        self.email = email
        self.api_key = api_key
        self.uid = None
        self.session = None
    
    def authenticate(self):
        endpoint = urljoin(self.db_url, '/jsonrpc')
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [
                    self.db_name,
                    self.email,
                    self.api_key,
                ],
            },
            "id": 1
        }        
        try:
            response = requests.post(endpoint, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            result = response.json()
            if 'result' in result and result['result']:
                self.uid = result['result']
                self.session = "authenticated"
                return True
            else:
                print(f"Authentication failed. Response: {result}")
                return False
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False
    
    def call_odoo(self, model, method, args=None, kwargs=None):
        if not self.uid:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        endpoint = urljoin(self.db_url, '/jsonrpc')
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.db_name,
                    self.uid,
                    self.api_key,
                    model,
                    method,
                    args or [],
                    kwargs or {}
                ]
            },
            "id": 1
        }
        
        try:
            response = requests.post(endpoint, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                raise Exception(result['error']['message'])
            
            return result['result']
        except Exception as e:
            print(f"Odoo API call failed: {str(e)}")
            raise
    
    def get_user_info(self):
        return self.call_odoo('res.users', 'read', [[self.uid]])
    
    def get_companies(self):
        return self.call_odoo('res.company', 'search_read', [[]], {'fields': ['name', 'id']})
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
        self.context = {}
    
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
    
    def get_user_companies(self):
        user_data = self.call_odoo(
            'res.users', 
            'read', 
            [[self.uid]], 
            {'fields': ['company_ids', 'company_id']}
        )
        
        if not user_data:
            return []
        company_ids = user_data[0].get('company_ids', [])
        if not company_ids:
            return []
        return self.call_odoo(
            'res.company', 
            'read', 
            [company_ids], 
            {'fields': ['name', 'id']}
        )
    
    def set_company_context(self, company_id):
        self.context['allowed_company_ids'] = [company_id]
        self.call_odoo(
            'res.users',
            'write',
            [[self.uid], {'company_id': company_id}]
        )

    def get_jobs(self, company_id=None):
        domain = []
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        return self.call_odoo(
            'hr.job', 
            'search_read', 
            [domain], 
            {'fields': ['name', 'company_id', 'description', 'no_of_recruitment']}
        )
    
    def get_candidates(self, job_id=None, company_id=None):
        domain = []
        if job_id:
            domain.append(('job_id', '=', job_id))
        elif company_id:
            domain.append(('company_id', '=', company_id))
        
        return self.call_odoo(
            'hr.applicant', 
            'search_read', 
            [domain], 
            {'fields': ['name', 'partner_name', 'email_from', 'stage_id', 'company_id', 'job_id', 'date_open', 'date_last_stage_update']}
        )
    
    def get_user_info(self):
        return self.call_odoo(
            'res.users', 
            'read', 
            [[self.uid]], 
            {'fields': ['id', 'name', 'email', 'company_id', 'company_ids']}
        )

    def get_companies(self):
        return self.call_odoo(
            'res.company', 
            'search_read', 
            [[]], 
            {'fields': ['id', 'name', 'country_id']}
        )
    
    def set_company_context(self, company_id):
        self.context['allowed_company_ids'] = [company_id]
        self.call_odoo(
            'res.users',
            'write',
            [[self.uid], {'company_id': company_id}]
        )
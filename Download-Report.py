import logging
import sys
import os,os.path,time
import json
import unicodedata
import datetime
from glob import glob
import urllib3
import requests

date = datetime.datetime.now()
mon = date.strftime('%m')
urllib3.disable_warnings()

p = "Path where report should be downloaded"
base_url = "BASE-URL"

class Nexpose:
    """
    Stateful handler for the Nexpose REST API.
    """

    def __init__(self, log_level=logging.INFO):

        # Craete a simple logger set to specific log level
        logging.basicConfig(
            format="%(asctime)s %(levelname)-8s %(message)s",
            filename='nexpose_reports.log',
            datefmt="%Y-%m-%d %H:%M:%S",
            level=log_level,
        )
        self.logger = logging.getLogger()
        self.session = requests.session()
        self.headers = {'Authorization': 'Basic encoded username and password goes here'}

    def request_reports(self, method,jsonbody=None):
        """
        Basic wrapper for requests using existing authentication, base URL,
        and other attributes for simplicity.
        """
        # Define base URL and issue request
        self.logger.info(f"Sending API call to {base_url}")
        resp = self.session.request(
            method=method,
            url=base_url,
            headers=self.headers,
            json=jsonbody,
            verify=False,
            allow_redirects=False
            )
        if resp.ok:
            self.logger.info(f"Successfully retrieved the list,Status code : {resp.status_code}")
        return resp
 
    def get_report_list(self,y):
        ''' gives report list '''
        report_dict = {}
        for i in range(len(y.values()[2])):
            name = y.values()[2][i]['name']
            id = y.values()[2][i]['id']
            report_dict[name] = id
        self.logger.info(f"Generated report dictionary : {report_dict}")
        return report_dict

    def generate_report(self,method,id):
        ''' generates reports '''
        self.session.request(
            method=method,
            url=f"{base_url}+'{id} + '/generate",
            headers=self.headers,
            verify=False,
            allow_redirects=False
        )
        self.logger.info(f"running report generation for report ID : {id}")

    def download_report(self,method,Repid_list):
        ''' downloads report '''
        for ID in Repid_list:
            resp = self.session.request(
                method=method,
                url=base_url+ '%s'%ID +'/history/latest/output',
                headers=self.headers,
                verify=False,
                allow_redirects=False
            )
            self.logger.info(f"Downloading Report for ID : {ID}")
#            lines = resp.text.encode('utf-8')
            with open (p+str(Repid_list.index(ID))+".csv", 'w') as f:
                f.write(resp.text)
        self.logger.info(f"Download Completed!!")
        sys.exit(0)

    def status_check(self,method,Repid_list):
        ''' checks status '''
        state_dict = {}
        for ID in Repid_list:
            resp = self.session.request(
                method=method,
                url=base_url+str(ID)+ '/history/latest',
                headers=self.headers,
                verify=False,
                allow_redirects=False
            )
            xyz = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'replace')
            data = json.loads(xyz)
#            status = str(data['resources'][0]['status'])
            status = str(data['status'])
#            size = str(data['resources'][0]['size']['formatted'])
            size = str(data['size']['formatted'])
#            gen_date = str(data['resources'][0]['generated'][:10])
            gen_date = str(data['generated'][:10])
            state_dict['%s'%ID] = [status,gen_date,size]
        return state_dict
if __name__ == '__main__':

    N = Nexpose()
    resp = N.request_reports('get')
    b = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'replace')
    y = json.loads(b)

    id1,id2 = (y['resources'][4]['id'],y['resources'][5]['id'])
    gen_mon = date.strftime('%b')
    Repid_list = [id1,id2]
    l = sorted(glob(p+/report*.csv'))
    month_list = [ time.ctime(os.path.getmtime(i)).split()[1] for i in l ]
    month_set = set(month_list)
    if len(l) == 2 and len(month_set) == 1 and month_set.pop() == gen_mon:
        N.logger.info(f"Reports already downloaded")
        sys.exit(0)
    else:

        Generating = False
        while True:
            state = N.status_check('get',Repid_list)
            Status_list = []
            Month_list = []
            for i in range(len(Repid_list)):
                Status_list.append(list(state.values())[i][0])
                Month_list.append(list(state.values())[i][1].split('-')[1])

            status_set = set(Status_list)
            month_set = set(Month_list)

            if Generating is False and len(status_set) == 1 and  \
         len(month_set) == 1 and status_set.pop() == 'complete' and  month_set.pop() == mon :
                N.download_report('get',Repid_list)
            elif Generating is False:
                generate_ids = []
                for key, value in state.items():
                    if mon not in value[1].split('-'):
                        generate_ids.append(key)
                if len(generate_ids) >= 1:
                    Generating = True
                    for i in range(len(generate_ids)):
                        N.generate_report('post',generate_ids[i])
                else:
                    Generating = False

#!/usr/bin/env python3

import prisma_sase
import io
import requests
import json
import csv
import os
import termtables as tt
import yaml
import argparse
import time


def sdk_login_to_controller(filepath):
    with open(filepath) as f:
        client_secret_dict = yaml.safe_load(f)
        client_id = client_secret_dict["client_id"]
        client_secret = client_secret_dict["client_secret"]
        tsg_id_str = client_secret_dict["scope"]
        global tsg
        tsg = tsg_id_str.split(":")[1]
        #print(client_id, client_secret, tsg)

    global sdk 
    sdk = prisma_sase.API(controller="https://sase.paloaltonetworks.com/", ssl_verify=False)
   
    sdk.interactive.login_secret(client_id, client_secret, tsg)
    print("--------------------------------")
    print("Script Execution Progress: ")
    print("--------------------------------")
    print("Login to TSG ID {} successful".format(tsg))

def get_epoch_time_range(t):
    now = time.time() * 1000 #milliseconds
    then = now - (t*60*60*1000) #milliseconds
    return int(then),int(now)

def list_all_gp_users(time_range):
    mu_status_url="https://pa-us01.api.prismaaccess.com/api/sase/v2.0/resource/custom/query/gp_mobileusers/user_login_list"

    header = {
            "prisma-tenant": tsg
    }
    sdk._session.headers.update(header)
    t1,t2 = get_epoch_time_range(time_range)
    payload = {
        "filter": {
        "rules":[
            {"property":"event_time",
            "operator":"between",
            "values":[t1,t2]
            }
        ]
        }
    }
    #print(payload)
    send_post(mu_status_url,header,payload)

def create_csv_output_file(Header, RList):
    with open('mu-status.csv', mode='w') as csv_file:
        csvwriter = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(Header)
        for Rec in RList:
            csvwriter.writerow(Rec)

def create_json_output_file():
    #create a dictionary
    data_dict = {}
 
    with open('mu-status.csv', encoding = 'utf-8') as csv_file_handler:
        csv_reader = csv.DictReader(csv_file_handler)
        i=0
        for rows in csv_reader:
            key = i
            data_dict[key] = rows
            i += 1

    with open('mu-status.json', 'w', encoding = 'utf-8') as json_file_handler:
       json_file_handler.write(json.dumps(data_dict, indent = 4))


def send_post(mu_status_url,header,payload):
    resp = sdk.rest_call(url=mu_status_url, data=payload, method="POST")
    print(resp)
    try:
        dataList = resp.json()["data"]
    except:
        print("No data found.")
        exit(0)
    print(resp.json())

    Header = ["GP-User-Name", "Client Private address", "User Source IP", "Country Name", "Login Time", "Logout Time"]
    RList = []
    index = 0
    for data in dataList:
        
        try: 
            logout_ts = data["logout_timestamp"]
        except:
            continue
        print(data)
        RList.append([data['gpuser_name'], data["client_private_address"], data["user_source_ip"],data["geoip_from_country_name"], data["login_timestamp"], data["logout_timestamp"]])
        index+=1

    table_string = tt.to_string(RList, Header, style=tt.styles.ascii_thin_double)

    create_csv_output_file(Header,RList)
    create_json_output_file()

    print(table_string)


def go():
    parser = argparse.ArgumentParser(description='Checking MU Status')
    parser.add_argument('-t1', '--T1Secret', help='Input secret file in .yml format for the tenant(T1) ',default="T1-secret.yml")
    parser.add_argument('-option', '--Option', help='user/loc/all to query based on user or location',default="all")
    parser.add_argument('-timerange', '--TimeRange', help='Time range in hours for which data needs to be fetched ',default=1)

    args = parser.parse_args()
    T1_secret_filepath = args.T1Secret
    option = args.Option
    time_range = int(args.TimeRange)

    #Pass the secret of 'from tenant' to login
    sdk_login_to_controller(T1_secret_filepath)

    #Check MU status
    list_all_gp_users(time_range)



if __name__ == "__main__":
    go()
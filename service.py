import io
import os
import sys
import json
import tempfile

import socket

from flask import Flask, abort, send_file, jsonify
from smb.SMBConnection import SMBConnection
from sesamutils import VariablesConfig, sesam_logger
from sesamutils.flask import serve
from validator import validate_file

APP = Flask(__name__)

logger = sesam_logger("cifs-reader", app=APP)

required_env_vars = ["username", "password", "hostname", "host", "share"]
optional_env_vars = ["schema_path"]
config = VariablesConfig(required_env_vars, optional_env_vars)
if not config.validate():
    sys.exit(1)

def create_connection():
    return SMBConnection(config.username, config.password, socket.gethostname(),
                         config.hostname, is_direct_tcp=True, use_ntlm_v2=True)


@APP.route("/<path:path>", methods=['GET'])
def process_request(path):
    try:
        if config.schema_path:
            schema_path = config.schema_path
    except AttributeError:
        schema_path = 'Denmark'
    
    logger.info(f"Processing request for path '{path}'.")

    conn = create_connection()
    if not conn.connect(config.host, 445):
        logger.error("Failed to authenticate with the provided credentials")
        conn.close()
        return "Invalid credentials provided for fileshare", 500

    logger.info("Successfully connected to SMB host.")

    logger.info("Listing available shares:")
    share_list = conn.listShares()
    for share in share_list:
        logger.info(f"Share: {share.name}  {share.type}    {share.comments}")

    path_parts = path.split("/")
    file_name = path_parts[len(path_parts)-1]

    try:
        with open('local_file', 'wb') as fp:
            conn.retrieveFile(config.share, path, fp)
            logger.info("Completed file downloading...")
            if schema_path != "Denmark":
                logger.info('Validator initiated...') 
                file_obj = tempfile.NamedTemporaryFile()
                conn.retrieveFile(config.share, path, file_obj)
                file_obj.seek(0)
                xml_content = file_obj.read().decode()    
                schema_obj = tempfile.NamedTemporaryFile()
                conn.retrieveFile(config.share, schema_path, schema_obj)
                schema_obj.seek(0)
                schema_content = schema_obj.read().decode()
                validation_resp = validate_file(xml_content, schema_content)
                logger.debug(f"This is the response from validation func : {validation_resp}")
                file_obj.close()
                schema_obj.close()
                if validation_resp == "Your xml file was validated :)":
                    return send_file('local_file', attachment_filename=file_name)
                else:
                    logger.error('Validation unsuccessfull! :(')
            else:    
                return send_file('local_file', attachment_filename=file_name)            
    except Exception as e:
        logger.error(f"Failed to get file from fileshare. Error: {e}")
        logger.debug("Files found on share:")
        file_list = conn.listPath(os.environ.get("share"), "/")
        for f in file_list:
            logger.debug('file: %s (FileSize:%d bytes, isDirectory:%s)' % (f.filename, f.file_size, f.isDirectory))
    finally:
        conn.close()
        os.remove("local_file")
    abort(500)

@APP.route("/bulk_read/<path:path>", methods=['GET'])
def folder_request(path):
    try:
        if config.schema_path:
            schema_path = config.schema_path
    except AttributeError:
        schema_path = 'Denmark'

    logger.info(f"Processing request for path '{path}'.")

    conn = create_connection()
    if not conn.connect(config.host, 445):
        logger.error("Failed to authenticate with the provided credentials")
        conn.close()
        return "Invalid credentials provided for fileshare", 500

    logger.info("Successfully connected to SMB host.")

    share_list = conn.listShares()
    for share in share_list:
        if share.name == os.environ.get("share"):
            target_share = share.name

    # Defined share of interest..
    logger.info(f"Writing target share from which we start : {target_share}")
    file_list = conn.listPath(target_share, f"/{path}")

    # Files to write to :
    files_to_send = []

    logger.info("Listing files found : %s" % file_list)
    for file_name in file_list:
        file_obj = tempfile.NamedTemporaryFile()
        path_to_file = f"/{path}/{file_name.filename}"
        try:
            conn.retrieveFile(target_share, path_to_file, file_obj)
            file_obj.seek(0)
            file_temp = file_obj.read().decode()
            if schema_path != "Denmark":
                logger.info('Validator initiated...')
                schema_obj = tempfile.NamedTemporaryFile()
                conn.retrieveFile(target_share, schema_path, schema_obj)
                schema_obj.seek(0)
                schema_content = schema_obj.read().decode()
                validation_resp = validate_file(file_temp, schema_content)
                logger.debug(f"This is the response from validation func : {validation_resp}")
                if validation_resp == "Your xml file was validated :)":
                    files_to_send.append(file_temp)
                else:
                    logger.error('Validation unsuccessfull! :(')
                    
                logger.info("Finished appending file to list")
                file_obj.close()
                schema_obj.close()
            else:
                files_to_send.append(file_temp)
                logger.info("Finished appending file to list")
                file_obj.close()
        except Exception as e:
            logger.error(f"Failed to get file from fileshare. Error: {e}")
    
    conn.close()
    logger.info(f"Finished appending files... ;)")
    return jsonify({'files' : files_to_send})

if __name__ == "__main__":
    logger.info("Starting service...")

    # Test connection at startup
    conn = create_connection()
    if not conn.connect(config.host, 445):
        logger.error("Failed to authenticate with the provided credentials")
    conn.close()

    serve(APP)

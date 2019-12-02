from lxml import etree, objectify
from lxml.etree import XMLSyntaxError
import logging

def validate_file(xml_file, xsd_file):
    try:
        try:
            xmlschema = etree.XMLSchema(file=xsd_file)
            logging.info(f"This is the xmlschema : {xmlschema}")
            parser = objectify.makeparser(schema=xmlschema)
            logging.info(f"Next step...")
            objectify.fromstring(xml_file, parser)
        except Exception as e:
            return f"Failed with error : {e}"
        return "Your xml file was validated :)"
    except XMLSyntaxError:
        return "Your xml file couldn't be validiated... :("


import os
import shutil
import sys

import xml.etree.ElementTree as ET


from .BaseConverter import BaseConverter
from ..RST_Writer import RST_Writer

from ..commons import *


def write_heritage_ref(writer, class_def, class_ref, prot):
    
    # button_options={"color":"dark", "outline":"", "ref-type":"myst", "expand":""}
    # writer.start_group("button-ref", title=class_ref, options=button_options)
    # writer.add_line(f"``{class_def.replace(" ","")}``")
    # writer.end_group("button-ref")
    # icon=" :octicon:`codescan;1em;sd-text-info` "
    writer.add_line(f"- :ref:`{make_cpp_code_to_text(class_def)} <{class_ref}>` ({prot})")
    writer.newline()

class ClassConverter(BaseConverter):
    def __init__(self, input_dir=".", output_dir="./rst"):
        super().__init__(input_dir, output_dir)


        self.rst_writer=RST_Writer()
        self.has_base=False
        self.has_deriv=False
        self.is_template=False
        self.my_type="Class"



    def convert(self, file):
        tree = ET.parse(file)
        root = tree.getroot()
        self.doc=root[0]

        # get name of class
        elem_name=self.doc.find("compoundname")
        self.class_name=(elem_name.text)

        self.parse_tparams()
        self.write_refs()
        self.write_include()
        self.write_brief()
        self.write_how_to_cite()
        self.write_detailed()
        self.write_list_bases()


        #######################################################
        ### Write to file
        #######################################################
        
        filename=f"{self.OUTPUT_DIR}/{subdir_classes}/{self.class_name}.rst"
        if self.is_template:
            filename=f"{self.OUTPUT_DIR}/{subdir_templates}/{self.class_name}.rst"
        
        self.rst_writer.write_to_file(filename)
        
        # return the name of written file
        return (filename)

    def parse_tparams(self):
        xml_tparam_list=self.doc.find("templateparamlist")
        self.tparam_types_list=[]
        self.tparam_names_list=[]
        if xml_tparam_list!=None:
            self.is_template=True
            self.my_type="Class Template"
            for xml_tparam in xml_tparam_list:
                if xml_tparam[0].text=="":
                    continue
                elif xml_tparam.find("declname")!=None:
                    self.tparam_types_list.append(xml_tparam.find("type").text)
                    self.tparam_names_list.append(xml_tparam.find("declname").text)
                else:
                    tparam_type, tparam_name=xml_tparam[0].text.split(" ")
                    self.tparam_types_list.append(tparam_type)
                    self.tparam_names_list.append(tparam_name)
    

    def write_refs(self):
        self.xml_class_ref=self.doc.get("id")
        self.class_ref=make_ref(f"{self.my_type} {self.class_name}")
        
        self.rst_writer.add_target(self.xml_class_ref)
        self.rst_writer.add_target(self.class_ref)
        self.rst_writer.start_section(make_cpp_code_to_text(self.class_name))

    def write_include(self):
        include=self.doc.find("includes")
        if include!=None:
            self.rst_writer.start_group("code-block", title="cpp")
            self.rst_writer+= f"#include <{include.text}>"
            self.rst_writer.end_group("code-block")

    def write_brief(self):
        brief=self.doc.find("briefdescription")
        self.rst_writer.start_group("card", title="Brief description")
        parse_brief(self.rst_writer, brief)
        self.rst_writer.end_group("card")
    
    def write_how_to_cite(self):
        self.rst_writer.start_section("How to reference this class", mark="-")
        write_how_to_cite(self.rst_writer, make_cpp_code_to_text(self.class_name), self.class_ref)
    
    def write_detailed(self):
        detail=self.doc.find("detaileddescription")
        self.rst_writer.start_section("Detailed description", mark="-")
        self.rst_writer.start_group("card")
        parse_brief(self.rst_writer, detail)
        self.rst_writer.end_group("card")


    def write_list_bases(self):
        list_elem_base=self.doc.findall("basecompoundref")
        if len(list_elem_base)>0:
            self.rst_writer.start_section("Inherits from", mark="-")
            self.has_base=True
            for child in list_elem_base:
                prot=child.get("prot")
                base_refid=child.get("refid")
                base_type="Class"
                base_name=child.text
                tparams=""
                if "<" in base_name:
                    base_type="Class Template"
                    base_name=child.text[:child.text.index("<")]
                    tparams=format_cpp_code(child.text[child.text.index("<"):])
                
                base_ref=make_ref(f"{base_type}-{base_name}")
                # do not use a ref in special cases
                if ("std::" in base_name or # no ref to standard library
                    base_name in self.tparam_names_list or  # no ref if inherits from type given by template param
                    base_name == "Problem"): # no ref to Problem from ICoCo
                    write_heritage_ref(self.rst_writer, child.text, "", prot)
                else:
                    write_heritage_ref(self.rst_writer, child.text, base_refid, prot)
                self.rst_writer.newline().newline()
#!/bin/python3

import os
import shutil
import sys
import argparse

import xml.etree.ElementTree as ET

from RST_Writer import RST_Writer







#######################################################
### Global parameters
#######################################################

subdir_classes="classes"
subdir_templates="templates"
subdir_enums="enums"
subdir_namespaces="namespaces"



def doxygen_warning(msg):
    print("WARNING: about doxygen (might be ill formed):")
    print(msg)

def code_warning(msg):
    print("WARNING: about code:")
    print(msg)

# sphinx refs are automatically converted to lowercase, alphanumeric only, with dashes between words.
# I do it manually to avoid confusion.
def make_ref(text):
    return_text=text
    
    return_text=return_text.replace("=", "-equal-")
    return_text=return_text.replace("*", "-ptr-")
    return_text=return_text.replace("&", "-ref-")
    return_text=return_text.replace("~", "-dtor-")
    
    replace_with_dash=["::", ",", "_", "<", ">", " ", "(", ")", "@", "\\"]
    for char in replace_with_dash:
        return_text=return_text.replace(char, "-")
    
    while "--" in return_text:
        return_text=return_text.replace("--", "-")
    if return_text[-1]=="-":
        return_text=return_text[:-1]
    return return_text.lower()

# useful to keep some special rst chars in function name/definition when not using code blocks
def make_cpp_code_to_text(text):
    # note: I dislike spaces between angles and tparams
    text=format_cpp_code(text)
    return text.replace("_","\\_").replace("*","\\*").replace("<","\\<").replace(">","\\>").replace("|", "\\|")

# not really doing as well as the name advertises
def format_cpp_code(code):
    out=code
    out=out.replace("@","") # from anonymous enums. this should really not be used
    out=out.replace("< ","<").replace(" >",">")
    out=out.replace("=", " = ")
    out=out.replace("+", " + ")
    out=out.replace("-", " - ")
    while "  " in out:
        out=out.replace("  "," ")
    out=out.replace("e - ", "e-")
    return out

def format_cpp_filename(cpp_filename):
    if "triocfd-code" in cpp_filename:
        loc=cpp_filename.split("triocfd-code")[1]
        return "triocfd-code"+loc
    if "trust-code" in cpp_filename:
        loc=cpp_filename.split("trust-code")[1]
        return "trust-code"+loc

def remove_excess_white_spaces(txt):
    return_txt=txt.replace('\n'," ")
    while "  " in return_txt:
        return_txt=return_txt.replace("  "," ")
    return return_txt

def parse_brief(writer, brief_xml):
    if brief_xml!=None:
        for child in brief_xml:
            if child.text:
                writer+= make_cpp_code_to_text(remove_excess_white_spaces(child.text)) + " " or " "
            for c in child:
                # consider all possible types manually. some might be missing. also, depth might be higher than 2
                # use operator+= and not add_line method because we may not want to start a new line.
                # maybe I'm wrong on this
                if c.tag=="ref":
                    refid=c.get("refid")
                    writer+= f":ref:`{make_cpp_code_to_text(c.text)} <{refid}>`" + " " # space at the end important because of remove_excess_white_spaces
                if c.tag=="verbatim":
                    writer+= make_cpp_code_to_text(remove_excess_white_spaces(c.text)) + " "
                if c.tail: # tail contains the text after a child node and before the next child
                    writer+= make_cpp_code_to_text(remove_excess_white_spaces(c.tail)) + " "
        writer.newline()
    return writer



def parse_enum(writer, enum):
    if enum.get("kind")!="enum" or enum.tag!="memberdef" :
        raise Exception(f"wrong enum xml")
    enum_xml_id=enum.get("id")
    enum_type=enum.find("type").text
    enum_name=enum.find("name").text
    xml_enum_qname=enum.find("qualifiedname")
    enum_qname=enum_name
    if xml_enum_qname!=None:
        enum_qname=xml_enum_qname.text
    enum_brief=enum.find("briefdescription")
    enum_detail=enum.find("detaileddescription")
    enum_loc=enum.find("location")
    
    if "@" in enum_qname:
        enum_qname=enum_qname.replace("@","")
        code_warning(f"used anonymous enum in enum {enum_qname}, this syntax is kinda weird, I recommend changing it.")
    
    enum_ref=make_ref(f"enum-{enum_type}-{enum_qname}")
    writer.add_target(enum_xml_id)
    writer.add_target(enum_ref)
    writer.start_section(make_cpp_code_to_text(enum_qname), mark="^")
    
    loc_filename=format_cpp_filename(enum_loc.get("file"))
    line=enum_loc.get("line")
    writer.add_line(f"**Location:** ``{loc_filename}:{line}``")
    
    writer.newline().add_line(f"**How to cite in this doc:**")
    
    write_how_to_cite(writer, make_cpp_code_to_text(enum_qname), enum_ref)
    
    
    writer.start_list("-")
    values=enum.findall("enumvalue")
    for val in values:
        vid=val.get("id")
        vn=make_cpp_code_to_text(val.find("name").text)
        writer.newline()
        writer.add_target(vid)
        writer.add_list_item(vn)
    writer.end_list("-")
    writer.newline()
    
    writer.name=enum_name
    
    return writer


def write_how_to_cite(writer, link_text, link_target): 
    writer.start_group("tab-set")
    writer.start_group("tab-item", title="RST")
    writer.start_group("code-block", title="rst")
    writer+= f":ref:`{link_text} <{link_target}>`"
    writer.end_group("code-block")
    writer.end_group("tab-item")
    writer.start_group("tab-item", title="Markdown")
    writer.start_group("code-block", title="md")
    writer+= f"[{link_text}](#{link_target})"
    writer.end_group("code-block")
    writer.end_group("tab-item")
    writer.end_group("tab-set")
    
# function which will convert an xml file describing a class into rst and write it to a file
# can choose between two modes: single file for all classes (heavy and slow on the web) 
# or one page per class (same as doxy html)
# in the future, maybe i will switch to a two step parsing to improve quality
# return name of written file, I may use that to cull unused file
def convert_class_to_rst(file, output_dir):
    tree = ET.parse(file)
    root = tree.getroot()
    doc=root[0]
    
    rst_writer=RST_Writer()
    has_base=False
    has_deriv=False
    is_template=False
    my_type="Class"
    
    xml_tparam_list=doc.find("templateparamlist")
    tparam_types_list=[]
    tparam_names_list=[]
    if xml_tparam_list!=None:
        is_template=True
        my_type="Class Template"
        for xml_tparam in xml_tparam_list:
            if xml_tparam[0].text=="":
                continue
            elif xml_tparam.find("declname")!=None:
                tparam_types_list.append(xml_tparam.find("type").text)
                tparam_names_list.append(xml_tparam.find("declname").text)
            else:
                tparam_type, tparam_name=xml_tparam[0].text.split(" ")
                tparam_types_list.append(tparam_type)
                tparam_names_list.append(tparam_name)
    
    elem_name=doc.find("compoundname")
    
    
    class_name=(elem_name.text)
    
    class_ref=make_ref(f"{my_type} {class_name}")
    xml_class_ref=doc.get("id")
    
    rst_writer.add_target(xml_class_ref)
    rst_writer.add_target(class_ref)
    rst_writer.start_section(make_cpp_code_to_text(class_name))
    

    
    include=doc.find("includes")
    if include!=None:
        rst_writer.start_group("code-block", title="cpp")
        rst_writer+= f"#include <{include.text}>"
        rst_writer.end_group("code-block")
        
    #######################################################
    ### Brief description
    #######################################################
    brief=doc.find("briefdescription")
    parse_brief(rst_writer, brief)
    
    #######################################################
    ### How to cite
    #######################################################
    rst_writer.start_section("How to cite this class in this doc", mark="-")
    write_how_to_cite(rst_writer, make_cpp_code_to_text(class_name), class_ref)
    
    #######################################################
    ### Detailed description
    #######################################################
    detail=doc.find("detaileddescription")
    rst_writer.start_section("Detailed description", mark="-")
    parse_brief(rst_writer, detail)
    
    
    #######################################################
    ### Bases
    #######################################################
    list_elem_base=doc.findall("basecompoundref")
    if len(list_elem_base)>0:
        rst_writer.start_section("Inherits from", mark="-")
        has_base=True
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
            
            base_ref=make_ref(f"{base_type} {base_name}")
            # do not use a ref in special cases
            if ("std::" in base_name or # no ref to standard library
                base_name in tparam_names_list or  # no ref if inherits from type given by template param
                base_name == "Problem"): # no ref to Problem from ICoCo
                rst_writer.rst += f"- {prot} : ``{make_cpp_code_to_text(base_name)}``"
            else:
                rst_writer.rst += f"- {prot} : :ref:`{make_cpp_code_to_text(base_name)} <{base_refid}>`"
            if tparams!="":
                rst_writer+=f" ``{tparams}``"
            rst_writer.newline().newline()
            
        
    
    #######################################################
    ### Derived classes
    #######################################################
    list_elem_deriv=doc.findall("derivedcompoundref")
    if len(list_elem_deriv)>0:
        rst_writer.start_section("Inherited by", mark="-")
        has_deriv=True
        for child in list_elem_deriv:                
            prot=child.get("prot")
            deriv_refid=child.get("refid")
            tparams=""
            deriv_type="Class"
            deriv_name=child.text
            if "<" in deriv_name:
                deriv_type="Class Template"
                deriv_name=make_cpp_code_to_text(child.text[:child.text.index("<")])
                tparams=format_cpp_code(child.text[child.text.index("<"):])
                
            deriv_ref=make_ref(f"{deriv_type} {deriv_name}")
            rst_writer +=f"- {prot} : :ref:`{make_cpp_code_to_text(deriv_name)} <{deriv_refid}>`"
            if tparams!="":
                rst_writer+=f" ``{tparams}``"
            rst_writer.newline().newline()
            

    
    #######################################################
    ### Graphs
    #######################################################
    # ~ rst_writer.start_section("Inheritance graph", mark="-")
    # ~ img=f"../../html/{class_refid}__inherit__graph.png"
    # ~ rst_writer.add_line(f".. image:: {img}")
    
    #### not used because very slow. Might reconsider
    # ~ generate_graphs=False
    # ~ if generate_graphs:
        # ~ inheritancegraph=doc.find("inheritancegraph")
        # ~ id_to_label={}
        # ~ if inheritancegraph!=None:
            # ~ rst_writer.start_group("dropdown", title="Inheritance graph", options={"open":""})
            # ~ rst_writer.start_group("digraph",title=class_name+"_graph") 
            # ~ for node in inheritancegraph:
                
                # ~ node_name=node.find("label").text
                # ~ id_to_label[node.get("id")]=node_name
                
            # ~ for node in inheritancegraph:
                # ~ node_name=node.find("label").text
                # ~ list_children=node.findall("childnode")
                # ~ for child in list_children:
                    # ~ refid=child.get("refid")
                    # ~ rst_writer.rst+=f"\"{node_name}\" -> \"{id_to_label[refid]}\";"
                    # ~ rst_writer.newline()
                    
            
            # ~ rst_writer.end_group("digraph")
            # ~ rst_writer.end_group("dropdown")
    
    
    #######################################################
    ### Member functions (of all kinds)
    #######################################################
    list_sections=doc.findall("sectiondef")
    section_types={
        "public-func":["List of Public Methods"],
        "protected-func":["List of Protected Methods"],
        "private-func":["List of Private Methods"],
        "public-static-func":["List of Public Static Methods"],
        "protected-static-func":["List of Protected Static Methods"],
        "private-static-func":["List of Private Static Methods"],
        }
    # used to append a section with all members at the end
    rst_list_all_members=RST_Writer(init_indent=0) 
    
    refs_template_spec=set()
    
    for section in list_sections:
        key=section.get("kind")
        if key in section_types:
            rst_writer.start_section(section_types[key][0], mark="-")
            rst_writer.start_list("-")
            for member in section:
                member_name=member.find("name").text
                member_virtual=member.get("virtual")
                member_prot=member.get("prot")
                xml_member_ref=member.get("id")
                member_static="static" if member.get("static") == "yes" else ""
                member_inline="inline" if member.get("inline") == "yes" else ""
                definition=member.find("definition").text.replace("< ","<").replace(" >",">")
                args=member.find("argsstring").text
                member_brief=member.find("briefdescription")
                member_detail=member.find("detaileddescription")
                member_in_body=member.find("inbodydescription")
                member_location=member.find("location").text
                member_tparam=member.find("templateparamlist")
                
                is_template_specialization=False
                
                if member_tparam!=None and member_tparam.find("param")==None:
                    is_template_specialization=True
                                
                member_type=f"Method {class_name}::"
                if "~" in member_name:
                    member_type=f"Dtor "
                if  member_name == class_name:
                    member_type=f"Ctor "
                    
                if args!=None:
                    code_full_def=(definition + args)
                    
                    print_name=make_cpp_code_to_text(member_name)
                    
                    member_ref=make_ref(f"{member_prot}-{code_full_def}")
                    # add underscore to method with name ending in _
                    # because _ will be removed, leading to same signature
                    # I have cases where both method (with _ at the end and not) are private, 
                    # with same params, completely identical signature in all aspects
                    # this is crazy...
                    ref_name = definition
                    if ref_name[-1]=="_":
                        ref_name+="-underscore-"
                    # also Perte_Charge_Reguliere has methods d() and D().
                    # fix will be ugly:
                    # assume longer function names will not have this problem
                    if len(member_name)==1 and member_name.lower()!=member_name:
                        ref_name+="-cap"
                        
                    member_ref=make_ref(f"{member_prot}-{member_static}-{ref_name}-{args}")
                        
                        
                    rst_writer.add_list_item(f":ref:`{print_name} <{xml_member_ref}>`")
                    # ~ rst_writer.start_group("card", title=print_name)#, options={"link":f"{make_ref(xml_member_ref)}", "link-type":"ref", "link-alt":"test"})
                    
                    # ~ rst_writer.add_line(f":ref:`{print_name} <{xml_member_ref}>`")
                    # ~ rst_writer.start_group("code-block", title="cpp")
                    # ~ rst_writer+=f"{code_full_def}"
                    # ~ rst_writer.end_group("code-block")
                    # ~ rst_writer.end_group("card")
                    
                    
                    # no custom ref to template specializations, only the one from doxygen
                    if not is_template_specialization:
                        rst_list_all_members.add_target(f"{member_ref}")
                    
                    # doxygen ref to template spec only on first occurence (limitation of doxygen, fixed in 1.14)
                    if not (is_template_specialization and (xml_member_ref in refs_template_spec)):
                        rst_list_all_members.add_target(f"{xml_member_ref}")
                        refs_template_spec.add(xml_member_ref)
                    
                        
                    rst_list_all_members.start_group("card", title=print_name)
                    rst_list_all_members.start_group("code-block", title="cpp")
                    rst_list_all_members+=code_full_def
                    rst_list_all_members.end_group("code-block")
                    rst_list_all_members.newline()
                    
                    parse_brief(rst_list_all_members, member_brief)
                    
                    rst_list_all_members.newline().newline()
                    
                    parse_brief(rst_list_all_members, member_detail)
                    
                    rst_list_all_members.newline().newline()
                    
                    xml_list_reimplements=member.findall("reimplements")
                    if len(xml_list_reimplements)>0:
                        rst_list_all_members+="**Reimplements**:"
                        rst_list_all_members.start_list("-")
                        
                        for xml_ref_func in xml_list_reimplements:
                            refid=xml_ref_func.get("refid")
                            referenced_name=make_cpp_code_to_text(xml_ref_func.text)
                            rst_list_all_members.add_list_item(f":ref:`{referenced_name} <{refid}>`")
                            
                        rst_list_all_members.end_list("-")
                    
                    xml_list_references=member.findall("references")
                    if len(xml_list_references)>0:
                        rst_list_all_members.start_group("dropdown", title="References")
                        rst_list_all_members.start_list("-")
                        
                        for xml_ref_func in xml_list_references:
                            refid=xml_ref_func.get("refid")
                            referenced_name=make_cpp_code_to_text(xml_ref_func.text)
                            rst_list_all_members.add_list_item(f":ref:`{referenced_name} <{refid}>`")
                            
                        rst_list_all_members.end_list("-")
                        rst_list_all_members.end_group("dropdown")
                        
                    xml_list_referencedby=member.findall("referencedby")
                    if len(xml_list_referencedby)>0:
                        rst_list_all_members.start_group("dropdown", title="Referenced By")
                        rst_list_all_members.start_list("-")
                        
                        for xml_ref_func in xml_list_referencedby:
                            refid=xml_ref_func.get("refid")
                            referenced_name=make_cpp_code_to_text(xml_ref_func.text)
                            rst_list_all_members.add_list_item(f":ref:`{referenced_name} <{refid}>`")
                            
                        rst_list_all_members.end_list("-")
                        rst_list_all_members.end_group("dropdown")
                        
                    
                    rst_list_all_members.start_group("dropdown", title="How to cite in this doc:")
                    
                    write_how_to_cite(rst_list_all_members, code_full_def, member_ref)
                    # ~ rst_list_all_members.start_group("tab-set")
                    # ~ rst_list_all_members.start_group("tab-item", title="RST")
                    # ~ rst_list_all_members.start_group("code-block", title="rst")
                    # ~ rst_list_all_members+= f":ref:`{code_full_def} <{member_ref}>`"
                    # ~ rst_list_all_members.end_group("code-block")
                    # ~ rst_list_all_members.end_group("tab-item")
                    # ~ rst_list_all_members.start_group("tab-item", title="Markdown")
                    # ~ rst_list_all_members.start_group("code-block", title="md")
                    # ~ rst_list_all_members+= f"TODO"
                    # ~ rst_list_all_members.end_group("code-block")
                    # ~ rst_list_all_members.end_group("tab-item")
                    # ~ rst_list_all_members.end_group("tab-set")
                    rst_list_all_members.end_group("dropdown")
                    
                    rst_list_all_members.end_group("card")
            rst_writer.end_list("-")
            
    #######################################################
    ### Member attributes (of all categories)
    #######################################################
    attrib_section_types={
        "public-attrib":["List of Public Attributes"],
        "protected-attrib":["List of Protected Attributes"],
        "private-attrib":["List of Private Attributes"],
        "public-static-attrib":["List of Public Static Attributes"],
        "protected-static-attrib":["List of Protected Static Attributes"],
        "private-static-attrib":["List of Private Static Attributes"],
        }
    # used to append a section with all members at the end
    rst_list_all_attribs=RST_Writer(init_indent=0) 
    for section in list_sections:
        key=section.get("kind")
        if key in attrib_section_types:
            for attrib in section:
                attrib_name=attrib.find("name").text
                attrib_type=attrib.find("type").text
                attrib_definition=attrib.find("definition").text
                attrib_initializer=attrib.find("initializer")
                
                attrib_xml_ref=attrib.get("id")
                attrib_prot=attrib.get("prot")
                attrib_constexpr=attrib.get("constexpr")
                attrib_static=attrib.get("static")
                attrib_mutable=attrib.get("mutable")
                
                attrib_brief=attrib.find("briefdescription")
                attrib_detail=attrib.find("detaileddescription")
                
                rst_list_all_attribs.add_target(f"{attrib_xml_ref}")
                # ~ rst_list_all_attribs.add_target(f"{attrib_ref}")
                rst_list_all_attribs.start_group("card", title=make_cpp_code_to_text(attrib_name) + f" ({attrib_prot})")
                rst_list_all_attribs.start_group("code-block", title="cpp")
                rst_list_all_attribs+=format_cpp_code(attrib_definition)

                if attrib_initializer!=None:
                    init_lines=attrib_initializer.text.split("\n")
                    for line in init_lines:
                        rst_list_all_attribs+=format_cpp_code(line)
                        rst_list_all_attribs.newline()
                    

                
                rst_list_all_attribs.end_group("code-block")
                rst_list_all_attribs.newline()
                
                parse_brief(rst_list_all_attribs, attrib_brief)
                
                rst_list_all_attribs.newline().newline()
                
                parse_brief(rst_list_all_attribs, attrib_detail)
                rst_list_all_attribs.end_group("card")
    

                
    
    #######################################################
    ### Complete Doc for Member functions
    #######################################################
    rst_writer.start_section("Complete Member Function Documentation", mark="-")
    rst_writer+=(rst_list_all_members.printout())
    rst_writer.newline()
    
    #######################################################
    ### Complete Doc for Attributes
    #######################################################
    rst_writer.start_section("Attributes Documentation", mark="-")
    rst_writer+=(rst_list_all_attribs.printout())
    rst_writer.newline()
    
    #######################################################
    ### Friends
    #######################################################
    found_friends=False
    rst_friends=RST_Writer()
    for section in list_sections:
        if section.get("kind") == "friend":
            found_friends=True
            for member in section:
                friend_id=member.get("id")
                friend_type=member.find("type").text
                friend_def=member.find("definition").text
                
                rst_friends.start_list("-")
                rst_friends.add_target(friend_id)
                rst_friends.add_list_item(f"{friend_def}")
                
                rst_friends.end_list("-")
    if found_friends:
        rst_writer.start_section("Friends", mark="-")
        rst_writer+=(rst_friends.printout())
        rst_writer.newline()
        
    #######################################################
    ### Member types (of all categories)
    #######################################################
    type_section_types={
        "public-type":["List of Public Types"],
        "protected-type":["List of Protected Types"],
        "private-type":["List of Private Types"],
        }
    # used to append a section with all members at the end
    rst_list_all_types=RST_Writer()
    rst_list_inner_enums=RST_Writer()
    found_enums=False
    for section in list_sections:
        key=section.get("kind")
        if key in type_section_types:
            for member in section:
                if member.get("kind")=="enum":
                    found_enums=True
                    parse_enum(rst_list_inner_enums,member)

    #######################################################
    ### Inner enums
    #######################################################
    if found_enums:
        rst_writer.start_section("Enums", mark="-")
        rst_writer+=(rst_list_inner_enums.printout())
        rst_writer.newline()



    #######################################################
    ### Write to file
    #######################################################
    
    filename=f"{output_dir}/{subdir_classes}/{class_name}.rst"
    if is_template:
        filename=f"{output_dir}/{subdir_templates}/{class_name}.rst"
    
    rst_writer.write_to_file(filename)
    
    # return the name of written file
    return (filename)



# for namespaces
def convert_namespace_to_rst(file, output_dir):
    tree = ET.parse(file)
    root = tree.getroot()
    doc=root[0]
    rst_writer=RST_Writer()
    
    elem_name=doc.find("compoundname")
    
    namespace_name=elem_name.text
    
    namespace_ref=make_ref(f"Namespace-{namespace_name}")
    if "@" in namespace_name:
        namespace_name="Anonymous Namespace " + namespace_name.replace("@","")
        namespace_ref=make_ref(f"{namespace_name}")
    
    doxy_namespace_ref=doc.get("id")
    
    
    rst_writer.add_target(doxy_namespace_ref)
    rst_writer.add_target(namespace_ref)
    rst_writer.start_section(namespace_name)
    
    # Brief description
    brief=doc.find("briefdescription")
    parse_brief(rst_writer, brief)
    
    # Detailed description
    detail=doc.find("detaileddescription")
    if detail is not None:
        rst_writer.start_section("Detailed Description", mark="-")
        parse_brief(rst_writer, detail)
    
    # Inner classes
    list_classes=doc.findall("innerclass")
    if len(list_classes)>0:
        rst_writer.start_section("Inner Classes", mark="-")
        for inner_class in list_classes:
            refid=inner_class.get("refid")
            prot=inner_class.get("prot")
            class_name=inner_class.text
            rst_writer.add_line(f"- {prot} : :ref:`{class_name} <{refid}>`")
        
    
    # Inner enums
    sections=doc.findall("sectiondef")
    if len(sections)>0:
        rst_writer.start_section("Enums", mark="-")
        rst_writer_inner_enum=RST_Writer()
        for section in sections:
            if section.get("kind")=="enum":
                for enum in section:
                    parse_enum(rst_writer_inner_enum,enum)
                
        rst_writer.append_rst(rst_writer_inner_enum)
        rst_writer.newline()
    
    # Files where used
    rst_writer.start_section("Namespace Locations", mark="-")
    list_files=doc.findall("location")
    for location in list_files:
        loc_filename=format_cpp_filename(location.get("file"))
        line=location.get("line")
        rst_writer.add_line(f"- ``{loc_filename}:{line}``")
    
    ### Write the file
    filename=f"{output_dir}/{subdir_namespaces}/{namespace_name}.rst".replace(" ", "_")
    rst_writer.write_to_file(filename)
    return (filename)
    
# for files
def convert_filexml_to_rst(file, output_dir):
    tree = ET.parse(file)
    root = tree.getroot()
    doc=root[0]
    
    elem_name=doc.find("compoundname")
    
    found_enums=False
    sections=doc.findall("sectiondef")
    for section in sections:
        if section.get("kind")=="enum":
            rst_writer_inner_enum=RST_Writer()
            for enum in section:
                parse_enum(rst_writer_inner_enum,enum)
                
                    
            ### Write the file
            
            filename=f"{output_dir}/{subdir_enums}/{rst_writer_inner_enum.name}.rst"
            rst_writer_inner_enum.write_to_file(filename)

    # TODO: global functions should be defined here


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Used to convert a xml tree generated by doxygen into rst format, for inclusion in a Sphinx documentation (much like breathe, but faster for big projects).')
                    
    parser.add_argument('-i', '--input', default="./xml", help="Path to directory containing the xml generated by Doxygen") 
    parser.add_argument('-o', '--output', default="./rst", help="Path to directory where rst files will be generated") 
    parser.add_argument('--keeprst', action='store_true', help="Option to keep previously generated rst. Default is deleting and regenerating all.")
    parser.add_argument('--test', action='store_true', help="Option to run in test mode: only parse specific files. Sphinx will show a lot of warnings because of missing references. Mostly used to work on looks")
    
    args=parser.parse_args(argv)
    
    return args

    
def run(args):
    if not args.keeprst and os.path.isdir(args.output):
        shutil.rmtree(args.output)
    
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    converters={
    "class":convert_class_to_rst,
    "struct":convert_class_to_rst,
    "namespace":convert_namespace_to_rst,
    "file":convert_filexml_to_rst,
    }
    
    test_list=[
        "Interprete",
        "Process",
        "Objet_U",
        "AbstractIO",
        "Triangle_32_64", 
        "TRUSTTab",
        "Matrice_Base",
        "Domaine_IJK",
        "TVAlloc",
        "TRUSTVect",
        "TRUSTProblem_sup_eqns",
        "ICoCo",
        "VEF_discretisation",
        "InnerType",
    ]
    
    tree = ET.parse(f'{args.input}/index.xml')
    root = tree.getroot()
    
    for child in root:
        for key in converters:
            file_refid=child.get('refid')
            file=f"{args.input}/{file_refid}.xml"
            if key==child.attrib["kind"]:
                if not args.test:
                    converters[key](file, args.output)
                else:
                    for s in test_list:
                        if s in child.get("refid").replace("__","_"):
                            print("Test mode: including", child.get("refid"))
                            converters[key](file, args.output)
                            break

    #######################################################
    ### Header files
    #######################################################

    headers=[
        ["Classes", subdir_classes, "doxy_classes.rst"],
        ["Templates", subdir_templates, "doxy_templates.rst"],
        ["Namespaces", subdir_namespaces, "doxy_namespaces.rst"],
        ["Enums", subdir_enums, "doxy_enums.rst"],
    ]
    opt={"maxdepth": 1, "glob":""}
    doxy_writer=RST_Writer()
    doxy_writer.start_section("Doxygen Documentation", mark="-")
    doxy_writer.start_group("toctree", options=opt)
    for data in headers:
        writer=RST_Writer()

        writer.start_section(data[0], mark="-")
        writer.start_group("toctree", options=opt)
        writer.add_line(f"./{data[1]}/*")
        writer.end_group("toctree")

        writer.write_to_file(f"{args.output}/{data[2]}", force=True)

        doxy_writer.add_line(f"./{data[2]}")
    
    doxy_writer.end_group("toctree")

    doxy_writer.write_to_file(f"{args.output}/index.rst", force=True)




if __name__ == "__main__":
    
    args=parse_args(sys.argv[0:])

    print(args)
    
    run(args)
 
    
    
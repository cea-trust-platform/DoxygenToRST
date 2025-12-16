


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



def write_how_to_cite(writer, link_text, link_target):
    writer.add_line("Copy the following pieces of RST/Markdown code to cite this element in other parts of the sphinx documentation (there is a copy button on the top-right when hovering the code block):")
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
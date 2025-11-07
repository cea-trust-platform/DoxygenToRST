
import os

class RST_Writer:
    def __init__(self, init_indent=0):
        self.rst="" # content of the rst file
        self.current_indent=init_indent
        self.current_group_tree=[] # used to check correct indentation
        self.current_line="" # maybe used later for chekcs
        self.current_list_tree=[]
        self.newline()
        
    def __iadd__(self, txt):
        self.rst+=txt
        return self
        
    def add_line(self, txt):
        self.rst+=txt
        self.current_line=txt
        self.newline()
        return self

    def reset_indent(self, val=0):
        self.current_indent=val
        self.newline()
        return self
    
    def indent(self):
        self.current_indent+=1
        return self
    
    def unindent(self):
        if self.current_indent==0:
            raise Exception(f"Cannot unindent below 0")
        self.current_indent-=1
        return self
        
    def newline(self):
        self.rst+="\n" + (" "*4*self.current_indent)
        self.current_line=""
        return self

    def add_target(self, target_text):
        self+=f".. _{target_text}:"
        self.newline().newline()
        return self

    
    def start_section(self,title, ref=None, mark="="):
        self.newline()
        if ref is not None:
            self.rst+=f".. _{ref}:"
            self.newline()
            self.newline()
            
        self+=title
        self.newline()
        self+=mark*len(title)
        self.newline().newline()
        return self

    # what I call a group here is a sphinx directive whose content must be indented
    # the group must be closed manually to manage indentation
    def start_group(self,group_type, title="",options={}):
        self.newline().newline()
        self.rst+=f".. {group_type}:: {title}"
        self.indent()
        for key in options:
            self.newline()
            self.rst+=f":{key}: {options[key]}"
        self.newline().newline()
        
        self.current_group_tree.append(group_type)
        return self
    
    def end_group(self,group_type):
        cur=self.current_group_tree.pop()
        if cur!= group_type:
            raise Exception(f"Wrong group closed: {group_type} instead of {cur}")
        self.unindent().newline().newline()
        
        return self
        
    # to manage lists
    def start_list(self,list_marker):
        self.newline().newline()
        # ~ if len(self.current_list_tree)!=0: # indent for sublists
            # ~ self.indent()
        self.current_list_tree.append(list_marker)
        return self
        
    def add_list_item(self, text):
        if len(self.current_list_tree)==0:
            raise Exception(f"Not in a list")
        self.rst += f"{self.current_list_tree[-1]} {text}"
        self.newline()
        return self
        
    def end_list(self,list_marker):
        cur=self.current_list_tree.pop()
        # ~ self.unindent().newline() # when to unindent ?
        if cur != list_marker:
            raise Exception(f"Wrong list closed: {list_marker} instead of {cur}")
        return self
        
        
    # to append rst text from a complete rst with base indent at 0
    def append_rst(self, other):
        for line in other.printout().split("\n"):
            self.rst+=" "*4*self.current_indent + line + "\n"
        return self
    
    # performs some syntax checks and returns the txt
    def printout(self):
        if len(self.current_group_tree)>0:
            raise Exception(f"Unclosed groups: {self.current_group_tree}")
        if len(self.current_list_tree)>0:
            raise Exception(f"Unclosed lists: {self.current_list_tree}")
        lines=self.rst.split("\n")
        out=""
        last_is_empty=False
        for line in lines:
            cur_is_empty=line.isspace() or len(line)==0
            if not cur_is_empty:
                out += line + "\n"
                last_is_empty=False
            elif not last_is_empty:
                out+=line + "\n"
            # ~ else:
                # ~ print("skip", len(line))
                
            last_is_empty=cur_is_empty
            
            
        return out
        
    def write_to_file(self, filename, force=False, mode="w"):
        # sanitize filename just in case (with github artifact invalid chars)
        invalid="\":<>|*?\r\n"
        for chr in invalid:
            filename=filename.replace(chr,"_")

        loc=os.path.dirname(filename)
        if not os.path.exists(loc):
            print(f"mkdir {loc}")
            os.makedirs(loc)

        if force or mode=="a" or not os.path.exists(filename):
            # print(f"write {filename}")
            with open(filename, mode) as f:
                f.write(self.printout())   
        return self.rst

import re
from cldfbench.catalogs import pyglottolog, Glottolog
import pybtex
import pandas as pd
import pycldf
import pathlib
import json
import pynterlinear as pynt
from pynterlinear import morpheme_delimiters

# glottolog = pyglottolog.Glottolog(Glottolog.from_config().repo.working_dir)

def valid_morpheme_ids(dataset, table, column, row):
    # gloss, morphemes = row[column.name], None
    col = table.get_column('http://cldf.clld.org/v1.0/terms.rdf#analyzedWord')
    col1 = table.get_column("Morpheme_IDs")
    col2 = table.get_column("Position_Identified")
    if col1:
        words = row[col.name]
        m_ids = row[col1.name]
        mask = row[col2.name]
    morphemes = []
    for word in words:
        for obj in pynt.split_word(word):
            if obj not in pynt.morpheme_delimiters:
                morphemes.append(obj)
    if len(morphemes) != len(mask):
        print(row["ID"])
        print(morphemes)
        print(mask)
        m_c = 0
        i_c = 0
        while m_c+1 < len(morphemes) and m_c+1 < len(mask):
            if mask[m_c]:
                print(f"{morphemes[m_c]}\t{mask[m_c]}\t{m_ids[i_c]}")
                i_c += 1
            else:
                print(f"{morphemes[m_c]}\t{mask[m_c]}\tNONE")
            m_c += 1
        raise ValueError(f'Number of morphemes ({len(morphemes)}) and morpheme IDs ({len(mask)}) does not match')

def morpheme_id_validator():
    return (
        None,
        'http://cldf.clld.org/v1.0/terms.rdf#gloss',
        valid_morpheme_ids
        )

def morpheme_mask_row():
    return {
        "name": "Position_Identified",
        "dc:description": "Positions of morphemes in the interlinear gloss and whether they are identified.",
        "required": False,
        "datatype": {"base": "boolean"},
        "separator": "; ",
    }
    
def custom_spec(component, column, separator):
    path = pathlib.Path(pycldf.__file__).resolve().parent.joinpath("components", f"{component}-metadata.json")
    metadata = json.load(open(path, "r"))
    for col in metadata["tableSchema"]["columns"]:
        if col["name"] == column:
            if separator:
                col["separator"] = separator
            elif "separator" in column:
                del col["separator"]
            return col

desired = {
    "book": ["author","year","title","subtitle","publisher","location"],
    "article": ["author","year","title","subtitle","journal","volume","number","issue","pages"],
    "collection": ["editor","year","title","subtitle","publisher","location"],
    "phdthesis": ["author","year","institution","location","title","subtitle"],
    "mastersthesis": ["author","year","institution","location","title","subtitle"],
    "incollection": ["author", "year", "booktitle", "editor", "publisher", "location", "subtitle", "booksubtitle"],
    "misc": ["author","year","title","subtitle","publisher","location"],
}

remaps = {
    "school": "institution",
    "address": "location"
}

def pad_ex(obj, gloss):
    out_obj = []
    out_gloss = []
    for o, g in zip(obj.split(" "), gloss.split(" ")):
        diff = len(o)-len(g)
        if diff < 0:
            o += " "*-diff
        else:
            g += " "*diff
        out_obj.append(o)
        out_gloss.append(g)
    return "  ".join(out_obj).strip(" "), "  ".join(out_gloss).strip(" ")

def deglottologify(src, key):
    db = pybtex.database.parse_string(src, "bibtex")
    entry = db.entries[key]
    wanted_fields = desired[entry.type]
    while len([item for item in entry.fields.keys() if item not in wanted_fields]) > 0:
        for field in entry.fields:
            if field in remaps:
                entry.fields[remaps[field]] = entry.fields[field]
                entry.fields._dict.pop(field)
                entry.fields.order.remove(field)
            elif field not in wanted_fields:
                entry.fields._dict.pop(field)
                entry.fields.order.remove(field)
    if "title" in entry.fields and ": " in entry.fields["title"]:
        entry.fields["title"], entry.fields["subtitle"] = entry.fields["title"].split(": ", 1)
    if "booktitle" in entry.fields and ":" in entry.fields["booktitle"]:
        entry.fields["booktitle"], entry.fields["booksubtitle"] = entry.fields["booktitle"].split(": ", 1)
    if "publisher" in entry.fields and ":" in entry.fields["publisher"]:
        entry.fields["location"], entry.fields["publisher"] = entry.fields["publisher"].split(": ", 1)
    return entry
    
    # def get_name(input):
    #     if "and" in input:
    #         input = input.split("and")[0]
    #     if "," in input:
    #         return input.split(",")[0].lower()
    #     else:
    #         return input.split(" ")[-1].lower()
    # if "editor" in output.keys():
    #     initial = get_name(output["editor"])
    # if "author" in output.keys():
    #     initial = get_name(output["author"])

def split_ref(ref):
    if "[" in ref:
        return ref.split("[")[0], re.search(r'\[(.*?)\]',ref).group(1)
    else:
        return ref, None
        
def decompose_pages(ref):
    bibkey, pages = split_ref(ref)
    return [f"{bibkey}[{p.strip()}]" for p in pages.split(",")]

def expand_pages(pages):
    out_pages = []
    for pranges in pages:
        for page in pranges.split(","):
            page = page.strip()
            if "-" in page:
                ps = page.split("-")
                if (ps[0].isdigit() and ps[1].isdigit()):
                    out_pages.extend(list(range(int(ps[0]), int(ps[1]))))
                else:
                    out_pages.append(page)
            else:
                out_pages.append(page)
    out_pages = [int(x) if (type(x)==int or x.isdigit()) else x for x in out_pages]
    numeric = [x for x in out_pages if type(x)==int]
    non_numeric = [x for x in out_pages if not type(x)==int]
    return sorted(set(numeric)), list(set(non_numeric))
        
def combine_pages(pages):
    numeric, non_numeric = expand_pages(pages)
    out_pages = []
    for page in numeric:
        if not out_pages:
            out_pages.append([page, page])
        else:
            if out_pages[-1][-1] == page-1:
                out_pages[-1][-1] = page
            else:
                out_pages.append([page, page])
    return ", ".join(non_numeric + [f"{x[0]}-{x[1]}" if x[0]!=x[1] else str(x[0]) for x in out_pages])
    
def combine_refs(refs):
    bibkeys = {}
    for ref in refs:
        bibkey, pages = split_ref(ref)
        if bibkey not in bibkeys:
            bibkeys[bibkey] = []
        if pages:
            bibkeys[bibkey].append(pages)
    out = []
    for bibkey, pages in bibkeys.items():
        out_string = bibkey
        if bibkey != "pc":
            page_string = combine_pages(pages)
        else:
            page_string = ", ".join(list(set(pages)))
        if pages:
            out_string += f"[{page_string}]"
        out.append(out_string)
    return out

def ipaify_ex(tokenizer, string):
    parts = pynt.split_word(string)
    out = []
    for part in parts:
        if part in morpheme_delimiters + [" "]:
            out.append(part)
        else:
            if ("�" in tokenizer(part, "mapping")):
                part = string.lower()
            out_string = tokenizer(part, "mapping").replace(" ", "").replace("#", " ")
            out.append(out_string)
            # if "�" in out_string:
            #     print(f"Can't convert\n{part}\n{out_string}")
    out = "".join(out)
    return out

def cite(refs, parens=False):
    if not parens:
        out_string = "\\textcite"
    else:
        out_string = "\\parencite"
    if not isinstance(refs, list):
        refs = [refs]
    else:
        out_string += "s"
    citations = []
    perscomm = []
    for ref in refs:
        if ref == "": continue
        if "pc[" not in ref:
            bibkey, pages = split_ref(ref)
            citations.append([pages, bibkey])
        else:
            pc, person = split_ref(ref)
            perscomm.append(person)
    if len(perscomm) > 0:
        citations[-1][0] += f"; p.c."
        for person in perscomm:
            citations[-1][0] += f", {person}"
    for page, key in citations:
        if page:
            out_string += f"[{page}]{{{key}}}"
        else:
            out_string += f"{{{key}}}"
    return out_string
    
def cite_a_bunch(refs, parens=False):
    return cite(combine_refs(refs), parens=parens)
    
def delatexify(source_list):
    all_citations = []
    if type(source_list) != list:
        source_list = [source_list]
    for inp in source_list:
        citations = []
        if "perscomm" in inp:
            bibkey = inp.split("{")[-1].replace("}","")
            citations.append(f"pc[{bibkey}]")
        elif "cite" not in inp:
            return inp
        else:
            sources = inp.split("cite", 1)[1].lstrip("s")
            for entry in sources.split("}")[0:-1]:
                p = re.search(r"\[([A-Za-z0-9_/]+)\]", entry)
                if p is not None:
                    p = "["+p.group(1)+"]"
                else:
                    p = ""
                bibkey = entry.split("{")[-1]
                citations.append(bibkey+p)
        all_citations.append(citations)
    return all_citations

def get_cognates(df, cogset_id, form_sep="+", cog_sep="+", cog_col="Cognates", form_col="Form"):
    cogs = []
    df = df[~(pd.isnull(df[cog_col]))]
    df = df[df[cog_col].apply(lambda x: cogset_id in x)]
    for i, row in df.iterrows():
        for j, (cogid, form) in enumerate(zip(row[cog_col].split(cog_sep), row[form_col].split(form_sep))):
            if cogid == cogset_id:
                cogs.append({
                    "Index": i,
                    "Form": form,
                    "Slice": j+1,
                })
    if len(cogs) == 0:
        return None
    out_df = pd.DataFrame.from_dict(cogs)
    out_df.set_index("Index", inplace=True)
    return out_df


if __name__=="__main__":
    print(cite_a_bunch(["alves2017arara[150]", "alves2017arara[151]", "alves2017arara[150-151]", "alves2017arara[152-153, 151]", "alves2017arara[153]", "alves2017arara[153]", "alves2017arara[xi-xii]", "alves2017arara[153]", "alves2017arara[151-153]"]))
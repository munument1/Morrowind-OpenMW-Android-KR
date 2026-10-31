#!/usr/bin/env python3
"""Verified Android KR12.4 data-only package; never changes APK or user files."""
import argparse,hashlib,json,re,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from patch_kr12_quest_entry_topics import chunks,fields,decoded
ASHA='59bbf4ef4a54f95f03778e16812e37b2b5aa10e35b9b1d7f4da36d744ca0f0bd'
WSHA='71fbbd1ae5506df4444fe47f31b29101f010a96fa5d73bb4b8699977cd211497'
OLD_ESP='c0cb2f5702da067e11820e5a11ffb4b758ea28e101779fc43a721072783ed253'
NEW_ESP='2276384ad93fd3e56bc0d401aacc45418ba38993ee798e0e1a7e09564a375d3a'
OLD_TOP='caf31e0703afcbcdb699c6df6e0d27f2250416821c18f6c12a711116de440730'
NEW_TOP='0516f17495afbdf5e3712d40aad9f11dc314edc7bd75ef33c9a8018b5fc60b16'
ADIR='Morrowind_Korean_ReTranslation/'
WDIR='payload/mods/Morrowind_Korean_ReTranslation/'
ESP='Morrowind_Korean_ReTranslation.esp'; TOP='Morrowind_Korean_ReTranslation.top'
def sha(b):return hashlib.sha256(b).hexdigest()
def visible(b):return re.sub(r'@([^#]+)#',lambda m:m.group(1),decoded(b))
def assert_esp(before,after):
    a=list(chunks(before,16));b=list(chunks(after,16))
    if len(a)!=len(b) or len(a)!=48146:raise ValueError('Record count mismatch')
    changed=[]
    for (type1,h,v),(type2,h2,w) in zip(a,b):
        if type1!=type2 or h[8:]!=h2[8:]:raise ValueError('TES3 record header drift')
        if v==w:continue
        if type1!=b'INFO':raise ValueError('Non-INFO changed')
        left=fields(v);right=fields(w)
        if len(left)!=len(right):raise ValueError('INFO field count changed')
        n=0
        info=decoded(dict(left).get(b'INAM',b''))
        for (k,x),(k2,y) in zip(left,right):
            if k!=k2:raise ValueError('INFO field type changed')
            if x==y:continue
            if k!=b'NAME' or visible(x)!=visible(y):raise ValueError('INFO condition/script or displayed text changed')
            n+=1
        if n!=1:raise ValueError('INFO NAME changed more than once')
        changed.append(info)
    if len(changed)!=91 or len(set(changed))!=91:raise ValueError('Not 91 unique INFO.NAME changes')
    return changed
def assert_top(a,b):
    x=a.decode('utf-8-sig').splitlines(keepends=True)
    y=b.decode('utf-8-sig').splitlines(keepends=True)
    if len(x)!=len(y):raise ValueError('TOP line count changed')
    changed=[(u,v) for u,v in zip(x,y) if u!=v]
    if len(changed)!=3:raise ValueError('Expected exactly 3 TOP alias updates')
    for u,v in changed:
        if u.split('\t',1)[0]!=v.split('\t',1)[0]:raise ValueError('Alias key changed')
    return len(changed)
def main():
    p=argparse.ArgumentParser()
    for n in ('source','windows','output','report'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if len({v.resolve() for v in (a.source,a.windows,a.output,a.report)})!=4 or a.output.exists() or a.report.exists():raise ValueError('Outputs must be new')
    if sha(a.source.read_bytes())!=ASHA or sha(a.windows.read_bytes())!=WSHA:raise ValueError('Released ZIP source SHA mismatch')
    with zipfile.ZipFile(a.source) as android,zipfile.ZipFile(a.windows) as windows:
        names=android.namelist()
        if len(names)!=len(set(names)) or android.testzip() or windows.testzip():raise ValueError('Invalid release ZIP')
        ae,at=ADIR+ESP,ADIR+TOP
        for key in (ae,at):
            if names.count(key)!=1:raise ValueError('Missing/duplicate Android member: '+key)
        old_esp,old_top=android.read(ae),android.read(at)
        new_esp,new_top=windows.read(WDIR+ESP),windows.read(WDIR+TOP)
        for label,value,expected in (('Android ESP',old_esp,OLD_ESP),('Android TOP',old_top,OLD_TOP),('Windows ESP',new_esp,NEW_ESP),('Windows TOP',new_top,NEW_TOP)):
            if sha(value)!=expected:raise ValueError(label+' SHA mismatch')
        changed=assert_esp(old_esp,new_esp)
        aliases=assert_top(old_top,new_top)
        updates={ae:new_esp,at:new_top}
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(a.output,'w') as out:
            for item in android.infolist():
                out.writestr(item,updates.get(item.filename,android.read(item.filename)))
    with zipfile.ZipFile(a.source) as old,zipfile.ZipFile(a.output) as newer:
        if newer.testzip() or old.namelist()!=newer.namelist():raise ValueError('Bad final ZIP')
        for name in old.namelist():
            if name not in (ae,at) and old.read(name)!=newer.read(name):raise ValueError('Other Android member changed: '+name)
    report={'version':'KR12.4-Android-DATA-ONLY','source_android_sha256':ASHA,'source_windows_sha256':WSHA,
      'source_esp_sha256':OLD_ESP,'new_esp_sha256':NEW_ESP,'source_top_sha256':OLD_TOP,'new_top_sha256':NEW_TOP,
      'changed_INFO_count':len(changed),'changed_INFO_ids':changed,'changed_TOP_alias_count':aliases,
      'unrelated_records_and_scripts_byte_identical':True,'displayed_Korean_unchanged':True,
      'other_android_zip_members_byte_identical':True,'zip_crc':'PASS',
      'new_android_apk':False,'native_patch_0016_included_in_android_apk':False,'physical_gameplay_verified':False,
      'output_sha256':sha(a.output.read_bytes())}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (a.output.parent/(a.output.name+'.sha256')).write_text(report['output_sha256']+'  '+a.output.name+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='changed_INFO_ids'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Audit embedded Mach-O deployment targets without importing native libraries."""
import json
import pathlib
import struct
import sys

MACH64 = b'\xcf\xfa\xed\xfe'
FAT = {b'\xca\xfe\xba\xbe':('>',False), b'\xca\xfe\xba\xbf':('>',True),
       b'\xbe\xba\xfe\xca':('<',False), b'\xbf\xba\xfe\xca':('<',True)}
ARM64 = 0x100000c

def native_minimums(data):
    if data[:4] != MACH64:
        return []
    if len(data) < 32:
        raise ValueError('Truncated Mach-O header')
    _,cpu,_,_,count,size,_,_=struct.unpack_from('<8I',data)
    if cpu != ARM64:
        raise ValueError('Native file has no Apple Silicon slice')
    if size>1024*1024 or len(data)<32+size:
        raise ValueError('Invalid Mach-O load commands')
    offset=32;minimums=[]
    for _ in range(count):
        if offset+8>32+size:raise ValueError('Invalid Mach-O command')
        command,length=struct.unpack_from('<II',data,offset)
        if length<8 or offset+length>32+size:raise ValueError('Invalid Mach-O command length')
        value=None
        if command==0x32 and length>=24:
            platform,value=struct.unpack_from('<II',data,offset+8)
            if platform!=1:raise ValueError('Native file is not a macOS build')
        elif command==0x24 and length>=16:
            value=struct.unpack_from('<I',data,offset+8)[0]
        if value is not None:minimums.append((value>>16,(value>>8)&255,value&255))
        offset+=length
    if not minimums:raise ValueError('Native file has no macOS deployment target')
    return minimums

def require_supported(data,target):
    minimums=native_minimums(data)
    if any(v>target for v in minimums):
        raise ValueError('Native dependency requires macOS '+'.'.join(map(str,max(minimums))))
    return minimums

def audit_file(file,target):
    with file.open('rb') as stream:
        header=stream.read(8)
        if header[:4] not in FAT:
            stream.seek(0);return require_supported(stream.read(1024*1024+32),target)
        endian,wide=FAT[header[:4]]
        count=struct.unpack_from(endian+'I',header,4)[0]
        if count>64:raise ValueError('Invalid universal binary')
        size=32 if wide else 20
        table=stream.read(count*size)
        if len(table)!=count*size:raise ValueError('Truncated universal binary')
        for index in range(count):
            cpu=struct.unpack_from(endian+'I',table,index*size)[0]
            if cpu==ARM64:
                offset=struct.unpack_from(endian+('Q' if wide else 'I'),table,index*size+8)[0]
                stream.seek(offset);return require_supported(stream.read(1024*1024+32),target)
        raise ValueError('Universal binary has no Apple Silicon slice')

def main():
    root=pathlib.Path(sys.argv[1]);target=(15,0,0);rows=[];errors=[]
    for file in sorted(root.rglob('*')):
        if not file.is_file() or file.is_symlink():continue
        try:
            minimums=audit_file(file,target)
            if minimums:rows.append({'file':str(file.relative_to(root)),'minimum_os':['.'.join(map(str,v)) for v in minimums]})
        except ValueError as error:errors.append({'file':str(file.relative_to(root)),'error':str(error)})
    print(json.dumps({'target':'15.0.0','native_files':len(rows),'files':rows,'errors':errors},indent=2))
    if errors:sys.exit(1)
    if not rows:raise SystemExit('No native files found')
if __name__=='__main__':main()

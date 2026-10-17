import time, sys
from importlib import metadata
start = time.time()
print('argv[0]=', sys.argv[0])
print('sys.executable=', sys.executable)
try:
    import google
    print('google:', getattr(google, '__file__', getattr(google, '__path__', 'no-file')))
except Exception as e:
    print('google import error:', repr(e))
try:
    import google.generativeai as genai
    print('genai imported, file:', getattr(genai, '__file__', 'no-file'))
except Exception as e:
    print('genai import error:', repr(e))
try:
    import google.protobuf as protobuf
    print('protobuf:', getattr(protobuf, '__file__', getattr(protobuf, '__path__', 'no-file')))
except Exception as e:
    print('protobuf import error:', repr(e))
for pkg in ['google-generativeai', 'google-api-core', 'protobuf']:
    try:
        print(pkg, 'version=', metadata.version(pkg))
    except Exception as e:
        print(pkg, 'version lookup error:', repr(e))
print('elapsed', time.time()-start)

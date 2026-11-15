import hashlib,json,subprocess,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from tournament import server
from tournament.prepare import prepare

class ServerTests(unittest.TestCase):
 def test_select_download_cleanup_and_origin_guard(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);results=root/'results';rid='fixture';run=results/rid;candidate=run/'candidate-1';candidate.mkdir(parents=True)
   _,task=prepare(server.ROOT/'examples/day_planner/Day Planner.html',root)
   source=Path(task.repository)/task.target_file;original=source.read_bytes();changed=original+b'\n<!-- fixture revision -->\n';source.write_bytes(changed)
   diff=subprocess.check_output(['git','diff','--binary','HEAD'],cwd=task.repository);source.write_bytes(original)
   subprocess.run(['git','bundle','create',str(run/'baseline.bundle'),'HEAD'],cwd=task.repository,check=True,capture_output=True)
   (run/'task.json').write_text(json.dumps({'base_sha':task.base_sha,'target_file':task.target_file,'request':'fixture'}))
   (candidate/'changes.diff').write_bytes(diff)
   (candidate/'result.json').write_text(json.dumps({'candidate':'candidate-1','model':'fixture','status':'ready','verification':'passed','cleanup':'confirmed','source_sha256':hashlib.sha256(changed).hexdigest()}))
   with patch.object(server,'RESULTS',results):
    http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);threading.Thread(target=http.serve_forever,daemon=True).start()
    base='http://127.0.0.1:'+str(http.server_port)
    def post(path,body,origin=None):
     headers={'Content-Type':'application/json','Host':'127.0.0.1:8787'}
     if origin:headers['Origin']=origin
     return urllib.request.urlopen(urllib.request.Request(base+'/api'+path,data=json.dumps(body).encode(),headers=headers),timeout=10)
    try:
     with post('/runs/fixture/select',{'candidate':'candidate-1'}) as r:selected=json.load(r)
     self.assertEqual(selected['patch_application'],'passed')
     with urllib.request.urlopen(base+selected['download']) as r:
      self.assertEqual(r.read(),diff);self.assertIn('attachment',r.headers['Content-Disposition'])
     with post('/runs/fixture/select',{'candidate':'candidate-1'}) as r:self.assertEqual(json.load(r),selected)
     with post('/runs/fixture/cleanup',{}) as r:self.assertEqual(json.load(r)['candidates'][0]['cleanup'],'confirmed')
     with self.assertRaises(urllib.error.HTTPError) as err:post('/runs',{},'https://untrusted.example')
     self.assertEqual(err.exception.code,403)
    finally:http.shutdown();http.server_close()

// 테스트용 가짜 수파베이스 (vendor/supabase.js 대신 끼워 넣음). 실제 서버 · 키 없음. mock_server.py 의 함수를 부름.
var supabase={createClient:function(url,key,opts){
  var SK=opts.auth.storageKey, listeners=[];
  function sess(){ try{ return JSON.parse(localStorage.getItem(SK)||'null'); }catch(e){ return null; } }
  return {
    auth:{
      getSession:async function(){ return {data:{session:sess()}}; },
      signInWithPassword:async function(o){ var r=await window.mockAuth(o.email,o.password); if(r.error) return {data:{},error:{message:r.msg||'Invalid login credentials',code:r.code||'invalid_credentials',status:400}}; var s={user:r.user,access_token:'t'}; localStorage.setItem(SK,JSON.stringify(s)); return {data:{user:r.user,session:s},error:null}; },
      getUser:async function(){ var s=sess(); if(!s) return {data:{user:null},error:{message:'Auth session missing!',status:400}}; var r=await window.mockGetUser(s.user.id); if(r.error) return {data:{user:null},error:r.error}; s.user=r.user; localStorage.setItem(SK,JSON.stringify(s)); return {data:{user:r.user},error:null}; },
      signUp:async function(o){ var r=await window.mockSignUp(o.email,o.password,(o.options||{}).data||{}); if(r.error) return {data:{},error:{message:r.error,code:r.code,status:r.status||400}}; if(r.nosession) return {data:{user:r.user,session:null},error:null}; var s={user:r.user,access_token:'t'}; localStorage.setItem(SK,JSON.stringify(s)); return {data:{user:r.user,session:s},error:null}; },
      signOut:async function(){ localStorage.removeItem(SK); listeners.forEach(function(f){ f('SIGNED_OUT',null); }); return {error:null}; },
      onAuthStateChange:function(f){ listeners.push(f); return {data:{subscription:{unsubscribe:function(){}}}}; }
    },
    rpc:function(fn,args){ var b={_r:null, range:function(a,c){ b._r=[a,c]; return b; }, then:function(res,rej){ var s=sess(); var pr=!s?Promise.resolve({data:null,error:{message:'not signed in',status:401}}):window.mockRpc(fn,s.user.id,args||{},b._r).then(function(r){ return r&&r.error?{data:null,error:r.error}:{data:(r&&('data' in r))?r.data:null,error:null}; }); return pr.then(res,rej); } }; return b; },
    from:function(t){ var q={_f:{},_gt:'',_r:[0,999],
      select:function(){ return q; }, eq:function(k,v){ q._f[k]=v; return q; }, gt:function(k,v){ q._gt=v; return q; }, order:function(){ return q; }, range:function(a,b){ q._r=[a,b]; return q; },
      then:function(res,rej){ var s=sess(); if(!s) return Promise.resolve({data:[],error:null}).then(res,rej); return window.mockSelect(s.user.id,q._f.app,q._gt,q._r[0],q._r[1]).then(function(d){ return d&&d.error?{data:null,error:d.error}:{data:d,error:null}; }).then(res,rej); },
      upsert:function(rows){ var s=sess(); return window.mockUpsert(s?s.user.id:'',rows).then(function(r){ return r&&r.error?{error:r.error}:{error:null}; }); }
    }; return q; },
    storage:{from:function(bucket){ var F=window.__mockFiles=window.__mockFiles||{}; return {
      upload:async function(path,file,opts){ var s=sess(); if(!s) return {data:null,error:{message:'not signed in',statusCode:'401'}}; var r=await window.mockStorage('upload',s.user.id,bucket,path,(file&&file.size)||0); if(r.error) return {data:null,error:{message:r.error,statusCode:String(r.status||403)}}; F[path]=file; return {data:{path:path},error:null}; },
      remove:async function(paths){ var s=sess(); var r=await window.mockStorage('remove',s?s.user.id:'',bucket,JSON.stringify(paths||[]),0); if(r.error) return {data:null,error:{message:r.error}}; (r.removed||[]).forEach(function(p){ delete F[p]; }); return {data:(r.removed||[]).map(function(p){ return {name:p}; }),error:null}; },
      download:async function(path){ var s=sess(); var r=await window.mockStorage('read',s?s.user.id:'',bucket,path,0); if(r.error) return {data:null,error:{message:r.error,statusCode:String(r.status||400)}}; return {data:F[path]||new Blob(['mock file'],{type:'application/pdf'}),error:null}; },
      createSignedUrl:async function(path,sec){ var s=sess(); var r=await window.mockStorage('read',s?s.user.id:'',bucket,path,0); if(r.error) return {data:null,error:{message:r.error,statusCode:String(r.status||400)}}; window.__lastSigned=path; return {data:{signedUrl:URL.createObjectURL(F[path]||new Blob(['mock'],{type:'text/plain'}))},error:null}; }
    }; }},
    channel:function(name){ var ch={_cb:null,_f:null, on:function(ev,f,cb){ ch._f=f; ch._cb=cb; return ch; }, subscribe:function(st){ (window.__rtChans=window.__rtChans||[]).push(ch); setTimeout(function(){ st&&st('SUBSCRIBED'); },10); return ch; } }; return ch; },
    removeChannel:function(ch){ window.__rtChans=(window.__rtChans||[]).filter(function(x){ return x!==ch; }); }
  };
}};
window.__rtEmit=function(rows){ (window.__rtChans||[]).forEach(function(ch){ var uid=String((ch._f||{}).filter||'').split('eq.')[1]; rows.forEach(function(r){ if(r.user_id===uid) ch._cb({new:r}); }); }); };

'use strict';
const $ = id => document.getElementById(id);
const RULES = {
  STRUCTURING: {name:'Repeated cash deposits',color:'#e0b777',why:'Several cash deposits add up to a larger amount.',rule:'At least 3 incoming cash deposits of €8,000 to under €10,000 on one account/day, totaling at least €24,000.',next:'Check the source of funds and whether there is a reasonable explanation for splitting the deposits.'},
  VELOCITY: {name:'Payment burst',color:'#b7a0eb',why:'Many completed payments happened within a short time.',rule:'At least 10 completed payments within a trailing hour, including both endpoints. The flag count is the peak window count; the amount includes triggering rows only.',next:'Compare with normal account activity and check the purpose and recipients of the payments.'},
  RAPID_MOVEMENT: {name:'Rapid money movement',color:'#83c7cf',why:'Money left soon after a similar amount arrived.',rule:'An outgoing payment of at least €9,000 within one hour after incoming funds, at 80–120% of the incoming amount. Incoming payments are context; the flag amount counts outgoing payments once.',next:'Inspect both sides of the flow: where the incoming funds came from and why the outgoing payment was made.'},
  HIGH_RISK_CORRIDOR: {name:'Higher-risk corridor',color:'#dc929f',why:'A large cross-border payment involved a higher-risk demo country.',rule:'A completed cross-border payment of at least €10,000 to a HIGH/CRITICAL-rated reference country. Ratings are demonstration fixtures.',next:'Check the purpose, recipient and supporting information. Country rating alone does not establish wrongdoing.'}
};
const fmt = new Intl.NumberFormat('en-GB');
const eur = value => new Intl.NumberFormat('en-IE',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(value);
const money = value => new Intl.NumberFormat('en-IE',{minimumFractionDigits:2,maximumFractionDigits:2}).format(value);
const pretty = value => value.toLowerCase().replaceAll('_',' ');
const element = (tag, text, cls) => {const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let selectedPayment=null, paymentPoints=[];
let data, days, active=null, page=0, rows=[], current=[], visibleAlerts=[], nodes=[], edges=[];
let zoom=1,pan={x:0,y:0},playing=false,timer=null;
const canvas=$('network'), ctx=canvas.getContext('2d');
let w=0,h=0;
const hash = text => [...text].reduce((n,c)=>(Math.imul(n,31)+c.charCodeAt(0))>>>0,7);
function option(select,value,text){const o=element('option',text);o.value=value;select.append(o);}
function boundsDay(){return days[Number($('day').value)];}
function scopedAlerts(){return data.alerts.filter(a=>a.day<=boundsDay()&&(!$('account').value||a.account===$('account').value)&&(!$('pattern').value||a.rule===$('pattern').value)&&['ALL','COMPLETED'].includes($('status').value));}
function update(){
  visibleAlerts=scopedAlerts();
  if(active&&!visibleAlerts.some(a=>a.id===active.id))active=null;
  const support=$('pattern').value?new Set(visibleAlerts.flatMap(a=>a.evidence)):null;
  current=data.transactions.filter(t=>t.day<=boundsDay()&&(!$('account').value||t.account===$('account').value)&&($('status').value==='ALL'||t.status===$('status').value)&&(!support||support.has(t.id)));
  $('payment-count').textContent=fmt.format(current.length);
  $('payment-value').textContent=eur(current.filter(t=>t.status==='COMPLETED').reduce((s,t)=>s+t.amount,0));
  $('account-count').textContent=new Set(current.map(t=>t.account)).size;
  $('alert-count').textContent=visibleAlerts.length;
  $('queue-count').textContent=visibleAlerts.length;
  $('day-label').textContent=boundsDay();
  $('scope').textContent=`Through ${boundsDay()} · ${$('pattern').value?'pattern evidence only':'account activity'} · ${active?'selected flag highlighted':'all visible flags highlighted'}`;
  if(selectedPayment&&!current.some(t=>t.id===selectedPayment.id))selectedPayment=null;
  renderQueue();renderInspector();buildGraph();renderLedger();
}
function selectAlert(a){selectedPayment=null;active=a;$('account').value=a.account;$('status').value='COMPLETED';$('pattern').value=a.rule;$('day').value=Math.max(Number($('day').value),days.indexOf(a.day));page=0;zoom=1;pan={x:0,y:0};update();}
function renderQueue(){
 const list=$('alerts');list.replaceChildren();
 if(!visibleAlerts.length){list.append(element('p','No daily flags match this view. This does not establish that an account is safe.','note'));return;}
 for(const a of [...visibleAlerts].sort((a,b)=>b.day.localeCompare(a.day)||a.id.localeCompare(b.id))){
   const rule=RULES[a.rule],button=element('button',undefined,'alert-card'+(active?.id===a.id?' selected':''));
   button.style.setProperty('--signal',rule.color);button.setAttribute('aria-pressed',String(active?.id===a.id));
   button.append(element('strong',rule.name));const line=element('small');line.append(element('span',`${a.account} / ${a.day}`),element('span',eur(a.amount)));button.append(line);button.addEventListener('click',()=>selectAlert(a));list.append(button);
 }
}
function selectPayment(t){selectedPayment=t;active=null;$('account').value=t.account;$('pattern').value='';page=0;zoom=1;pan={x:0,y:0};update();}
function renderInspector(){
 const panel=$('inspector');panel.replaceChildren();panel.append(element('p','02 — FOLLOW THE EVIDENCE','eyebrow'));
 if(selectedPayment){
   const t=selectedPayment;panel.append(element('h3',t.id),element('p',`${pretty(t.kind)} · ${pretty(t.status)}`));
   panel.append(element('div',`${eur(t.amount)} · ${t.timestamp.replace('T',' ').replace('Z',' UTC')}`,'evidence-summary'));
   panel.append(element('h4','Recorded connection'),element('p',t.direction==='INCOMING'?`Unidentified source → ${t.account}`:`${t.account} → ${t.beneficiary||'unidentified recipient'}`));
   const related=data.alerts.filter(a=>a.day<=boundsDay()&&a.evidence.includes(t.id));
   panel.append(element('h4',related.length?'Supporting AML flags':'No rule flags in this snapshot'));
   if(!related.length)panel.append(element('p','No matching flag is not a guarantee that the payment is safe.'));
   for(const a of related){const button=element('button',RULES[a.rule].name,'secondary');button.style.margin='5px 0';button.addEventListener('click',()=>selectAlert(a));panel.append(button);}
   panel.append(element('p',`Recorded country: ${t.country} · channel: ${t.channel}. No inferred location or account ownership.`,'note'));
   const clear=element('button','Return to all accounts','secondary');clear.style.marginTop='16px';clear.addEventListener('click',reset);panel.append(clear);return;
 }
 if(!active){panel.append(element('h3','Select a flag.'),element('p','Isolate the account, follow the highlighted payments, and inspect the rule behind the signal.'));return;}
 const r=RULES[active.rule];panel.style.setProperty('--signal',r.color);
 panel.append(element('h3',r.name),element('p',r.why),element('div',`${active.account} · ${active.day}\n${active.evidence.length} supporting payment(s)\n${eur(active.amount)} in counted payments`,'evidence-summary'));
 panel.querySelector('.evidence-summary').style.whiteSpace='pre-line';
 panel.append(element('h4','What a reviewer could check'),element('p',r.next));
 const details=element('details');details.append(element('summary','Exact rule and evidence count'),element('p',r.rule),element('p',`SQL evidence count: ${active.count}. Supporting rows: ${active.evidence.length}. These can differ because supporting rows include context.`));panel.append(details);
 panel.append(element('p',`${active.id}\nRules: ${active.version}\nDaily snapshot / recommendation to review`,'version'));
 const clear=element('button','Return to all accounts','secondary');clear.style.marginTop='16px';clear.addEventListener('click',reset);panel.append(clear);
}
function buildGraph(){
 const map=new Map(),edgeMap=new Map(),signalByTx=new Map();
 for(const a of (active?[active]:visibleAlerts))for(const id of a.evidence){if(!signalByTx.has(id))signalByTx.set(id,[]);signalByTx.get(id).push(a.rule);}
 const add=(id,kind,account)=>{if(!map.has(id))map.set(id,{id,kind,account});};
 for(const t of current){
   add(t.account,'bank',t.account);
   const incoming=t.direction==='INCOMING';
   const other=incoming?`UN-IN-${t.account}`:(t.beneficiary||`UN-OUT-${t.account}`);
   add(other,other.startsWith('UN-')?'unknown':'external',t.account);
   const from=incoming?other:t.account,to=incoming?t.account:other,key=`${from}/${to}/${t.status}`;
   if(!edgeMap.has(key))edgeMap.set(key,{from,to,amount:0,transactions:[],signals:new Set(),status:t.status});
   const e=edgeMap.get(key);e.transactions.push(t);e.amount+=t.amount;for(const code of signalByTx.get(t.id)||[])e.signals.add(code);
 }
 nodes=[...map.values()];edges=[...edgeMap.values()];
 const banks=nodes.filter(n=>n.kind==='bank').sort((a,b)=>a.id.localeCompare(b.id));
 const focused=banks.length===1;
 banks.forEach((n,i)=>{n.x=focused?.48:.38+(hash(n.id)%100)/100*.25;n.y=focused?.5:.12+(i+.5)/banks.length*.75;});
 for(const n of nodes.filter(n=>n.kind!=='bank')){
   const inbound=n.id.startsWith('UN-IN');n.x=inbound?.10+(hash(n.id)%40)/1000:.78+(hash(n.id)%100)/1000;
   n.y=focused?(inbound?.3:n.kind==='external'?.44:.72):.1+(hash(n.id+'y')%1000)/1000*.78;
 }
 for(const n of nodes){n.signals=new Set(edges.filter(e=>e.from===n.id||e.to===n.id).flatMap(e=>[...e.signals]));}
 $('graph-empty').hidden=current.length>0;
 $('network-caption').textContent=`${banks.length} bank accounts / ${nodes.filter(n=>n.kind==='external').length} identified external beneficiaries / ${nodes.filter(n=>n.kind==='unknown').length} unresolved groups`;
 draw();
}
function position(n){return {x:(n.x*w-w/2)*zoom+w/2+pan.x,y:(n.y*h-h/2)*zoom+h/2+pan.y};}
function draw(){
 if(!w||!h)return;
 paymentPoints=[];ctx.clearRect(0,0,w,h);
 ctx.fillStyle='#282c32';for(let x=18;x<w;x+=28)for(let y=38;y<h-20;y+=28){ctx.beginPath();ctx.arc(x,y,.55,0,Math.PI*2);ctx.fill();}
 const map=new Map(nodes.map(n=>[n.id,n]));
 for(const e of [...edges].sort((a,b)=>a.signals.size-b.signals.size)){
   const a=position(map.get(e.from)),b=position(map.get(e.to));const color=e.signals.size===1?RULES[[...e.signals][0]].color:e.signals.size>1?'#ededf1':'#7e8590';
   const bend=Math.min(130,Math.abs(b.x-a.x)*.6);const c1={x:a.x+bend,y:a.y},c2={x:b.x-bend,y:b.y};
   ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.bezierCurveTo(c1.x,c1.y,c2.x,c2.y,b.x,b.y);ctx.strokeStyle=color;ctx.globalAlpha=e.signals.size?.72:active?.10:.18;ctx.lineWidth=Math.min(3.5,.55+Math.log10(1+e.amount)*.35);ctx.setLineDash(e.status==='COMPLETED'?[]:[3,5]);ctx.stroke();ctx.setLineDash([]);
   ctx.globalAlpha=e.signals.size?.9:.3;const t=.86;const point=u=>({x:(1-u)**3*a.x+3*(1-u)**2*u*c1.x+3*(1-u)*u*u*c2.x+u**3*b.x,y:(1-u)**3*a.y+3*(1-u)**2*u*c1.y+3*(1-u)*u*u*c2.y+u**3*b.y});const q=point(t),prev=point(t-.015),angle=Math.atan2(q.y-prev.y,q.x-prev.x);ctx.beginPath();ctx.moveTo(q.x,q.y);ctx.lineTo(q.x-4*Math.cos(angle-.45),q.y-4*Math.sin(angle-.45));ctx.lineTo(q.x-4*Math.cos(angle+.45),q.y-4*Math.sin(angle+.45));ctx.closePath();ctx.fillStyle=color;ctx.fill();
   for(const tx of e.transactions){
     const involved=(active?[active]:visibleAlerts).filter(a=>a.evidence.includes(tx.id));
     const codes=[...new Set(involved.map(a=>a.rule))];
     const u=.08+(hash(tx.id)%840)/1000;
     const dot=point(u);const selected=selectedPayment?.id===tx.id;
     ctx.globalAlpha=selected?1:codes.length?.95:.34;
     ctx.fillStyle=selected?'#ffffff':codes.length===1?RULES[codes[0]].color:codes.length?'#ededf1':'#b9bec7';
     const radius=selected?4:codes.length?1.8:.75;
     ctx.beginPath();ctx.arc(dot.x,dot.y,radius,0,Math.PI*2);ctx.fill();
     paymentPoints.push({x:dot.x,y:dot.y,tx});
   }
 }
 ctx.globalAlpha=1;
 for(const n of nodes){const p=position(n),color=n.signals.size===1?RULES[[...n.signals][0]].color:n.signals.size>1?'#f0f0f2':'#b8bcc5';const r=$('account').value?6:n.kind==='bank'?3.3:2.2;
   if(n.signals.size){ctx.beginPath();ctx.arc(p.x,p.y,r+4,0,Math.PI*2);ctx.strokeStyle=color;ctx.globalAlpha=.4;ctx.lineWidth=1;ctx.stroke();ctx.globalAlpha=1;}
   ctx.beginPath();if(n.kind==='unknown'){ctx.moveTo(p.x,p.y-r);ctx.lineTo(p.x+r,p.y);ctx.lineTo(p.x,p.y+r);ctx.lineTo(p.x-r,p.y);ctx.closePath();}else ctx.arc(p.x,p.y,r,0,Math.PI*2);
   ctx.fillStyle=n.kind==='bank'?color:'#0e1012';ctx.strokeStyle=color;ctx.lineWidth=1;ctx.fill();ctx.stroke();
   if($('account').value||zoom>2.2){ctx.font='10px monospace';ctx.fillStyle='#c3c7cf';ctx.textAlign='center';let label=n.kind==='unknown'?(n.id.startsWith('UN-IN')?'Unidentified sources':'Unidentified recipients'):n.id;ctx.fillText(label,p.x,Math.min(h-35,p.y+22));}
 }
}
function resize(){const rect=canvas.getBoundingClientRect();w=rect.width;h=rect.height;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=w*dpr;canvas.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);draw();}
function renderLedger(){
 const selectedIds=selectedPayment?new Set([selectedPayment.id]):active?new Set(active.evidence):null;rows=(selectedIds?current.filter(t=>selectedIds.has(t.id)):current).slice().sort((a,b)=>b.timestamp.localeCompare(a.timestamp)||a.id.localeCompare(b.id));
 $('ledger-title').textContent=selectedPayment?'Selected payment':active?'Supporting payments for this flag':'Payments behind the network';
 $('ledger-note').textContent=active?'Counted rows contribute to the alert amount. Context rows explain the pattern and are not added to that amount.':'All matching records are available across pages and in the export. Values use fixed synthetic exchange rates.';
 const count=Math.max(1,Math.ceil(rows.length/12));page=Math.max(0,Math.min(page,count-1));const body=$('transactions');body.replaceChildren();
 for(const t of rows.slice(page*12,page*12+12)){
  const tr=element('tr');let cell=element('td');const button=element('button',t.id,'transaction-link');button.addEventListener('click',()=>selectPayment(t));cell.append(button);cell.append(element('small',t.timestamp.replace('T',' ').replace('Z',' UTC')));tr.append(cell);
  const other=t.direction==='INCOMING'?'Unknown source':t.beneficiary||'Unknown recipient';tr.append(element('td',t.direction==='INCOMING'?`${other} → ${t.account}`:`${t.account} → ${other}`));tr.append(element('td',pretty(t.kind)),element('td',money(t.amount)),element('td',pretty(t.status)),element('td',active?(active.counted.includes(t.id)?'Counted':'Context'):'—'));body.append(tr);
 }
 if(!rows.length){const tr=element('tr'),td=element('td','No records match these filters.');td.colSpan=6;tr.append(td);body.append(tr);}
 $('page-count').textContent=`${fmt.format(rows.length)} records · page ${page+1} / ${count}`;$('previous').disabled=page===0;$('next').disabled=page>=count-1;
}
function reset(){stop();selectedPayment=null;active=null;page=0;zoom=1;pan={x:0,y:0};$('account').value='';$('pattern').value='';$('status').value='COMPLETED';$('day').value=days.length-1;update();}
function stop(){playing=false;clearInterval(timer);$('play').textContent='▶';$('play').setAttribute('aria-label','Play recorded days');draw();}
function download(){const fields=['id','account','beneficiary','timestamp','amount','direction','kind','country','status','channel'];const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';const csv=[fields.join(','),...rows.map(t=>fields.map(k=>quote(t[k])).join(','))].join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=element('a');a.href=url;a.download='northstar-synthetic-view.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
let drag=null;
canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,px:pan.x,py:pan.y};canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(drag){pan={x:drag.px+e.clientX-drag.x,y:drag.py+e.clientY-drag.y};draw();return;}const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,n=nodes.find(n=>{const p=position(n);return Math.hypot(p.x-x,p.y-y)<10;});const tip=$('tooltip');tip.hidden=!n;if(n){tip.textContent=n.kind==='unknown'?`Unidentified counterparties for ${n.account}; no shared identity is established.`:`${n.id} · ${n.kind==='bank'?'bank account':'external beneficiary'}${n.signals.size?' · review signal':''}`;tip.style.left=Math.max(8,Math.min(x+12,w-230))+'px';tip.style.top=Math.max(30,Math.min(y+12,h-75))+'px';}});
canvas.addEventListener('pointerup',e=>{if(!drag)return;const moved=Math.hypot(e.clientX-drag.x,e.clientY-drag.y);drag=null;if(moved<5){const r=canvas.getBoundingClientRect();const n=nodes.find(n=>{const p=position(n);return Math.hypot(p.x-e.clientX+r.left,p.y-e.clientY+r.top)<12;});if(n){selectedPayment=null;active=null;$('account').value=n.account;page=0;zoom=1;pan={x:0,y:0};update();}else{const point=paymentPoints.find(p=>Math.hypot(p.x-e.clientX+r.left,p.y-e.clientY+r.top)<5);if(point)selectPayment(point.tx);}}});
canvas.addEventListener('pointercancel',()=>drag=null);canvas.addEventListener('pointerleave',()=>{$('tooltip').hidden=true;});
canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','0'].includes(e.key)){e.preventDefault();if(e.key==='0'){zoom=1;pan={x:0,y:0};}else if(e.key==='+')zoom=Math.min(5,zoom*1.2);else if(e.key==='-')zoom=Math.max(.5,zoom/1.2);else{pan.x+=e.key==='ArrowLeft'?25:e.key==='ArrowRight'?-25:0;pan.y+=e.key==='ArrowUp'?25:e.key==='ArrowDown'?-25:0;}draw();}});
async function start(){try{
 const response=await fetch('data.json');if(!response.ok)throw new Error('Snapshot request failed');data=await response.json();if(data.schema_version!==1||!data.synthetic)throw new Error('Unsupported snapshot');
 days=[...new Set(data.transactions.map(t=>t.day))].sort();if(!days.length)throw new Error('Empty snapshot');
 for(const a of data.accounts)option($('account'),a.id,`${a.id} · ${a.customer}`);for(const [code,rule]of Object.entries(RULES))option($('pattern'),code,rule.name);
 $('day').max=days.length-1;$('day').value=days.length-1;$('provenance').textContent=`${data.provenance} Rules version: ${data.rules_version}.`;
 $('loading').hidden=true;$('app').hidden=false;
 for(const id of ['account','pattern','status'])$(id).addEventListener('change',()=>{selectedPayment=null;active=null;page=0;zoom=1;pan={x:0,y:0};update();});
 $('day').addEventListener('input',()=>{stop();page=0;update();});$('reset').addEventListener('click',reset);
 $('zoom-in').addEventListener('click',()=>{zoom=Math.min(5,zoom*1.25);draw();});$('zoom-out').addEventListener('click',()=>{zoom=Math.max(.5,zoom/1.25);draw();});$('fit').addEventListener('click',()=>{zoom=1;pan={x:0,y:0};draw();});
 $('previous').addEventListener('click',()=>{page--;renderLedger();});$('next').addEventListener('click',()=>{page++;renderLedger();});$('download').addEventListener('click',download);
 $('play').addEventListener('click',()=>{if(playing){stop();return;}selectedPayment=null;active=null;playing=true;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','Pause recorded days');if(Number($('day').value)===days.length-1)$('day').value=0;update();timer=setInterval(()=>{if(Number($('day').value)>=days.length-1){stop();return;}$('day').value=Number($('day').value)+1;page=0;update();},1000);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});new ResizeObserver(resize).observe(canvas);update();resize();
 }catch(err){$('app').hidden=true;$('loading').textContent='The demo could not load its snapshot. Please reload, or open the project repository for the local setup.';console.error(err);}}
start();

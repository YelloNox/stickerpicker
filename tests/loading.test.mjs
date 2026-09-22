import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {test} from 'node:test'
const load = async path => import('data:text/javascript;base64,' + Buffer.from(readFileSync(path)).toString('base64'))
const {fetchJSON} = await load(new URL('../web/src/pack-loader.js', import.meta.url))
const source = readFileSync(new URL('../web/src/index.js', import.meta.url), 'utf8')
const body = source.split('\tasync _loadPacks(disableCache = false) {')[1].split('\n\tcomponentDidMount()')[0].replace(/\n\t}\n$/, '')
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor
const run = new AsyncFunction('fetchJSON','INDEX','PACKS_BASE_URL','setGiphyAPIKey','disableCache',body)
function app() { return {state:{packs:[],loading:true},stickersByID:new Map(),updateFrequentlyUsed(){},setState(value){Object.assign(this.state,typeof value==='function'?value(this.state):value)}} }
test('pack loader exits loading for empty index, malformed JSON and missing packs', async () => {
 for (const [responses, expectError] of [[[{packs:[]}],false],[[{packs:['x.json']},new Error('invalid JSON')],true],[[{}],true],[[{packs:['x.json']},{stickers:[]}],false],[[{packs:['x.json']},{stickers:[{url:'mxc://a/b',id:'1'}]}],false]]) {
  const instance=app()
  await run.call(instance,async()=>{const next=responses.shift();if(next instanceof Error)throw next;return next},'index.json','packs',()=>{},false)
  assert.equal(instance.state.loading,false)
  assert.equal(!!instance.state.error,expectError)
 }
})
test('fetch helper names HTTP errors and invalid JSON; times out stalled response bodies',async()=>{
 const original=globalThis.fetch
 try {
  globalThis.fetch=async()=>({ok:false,status:404})
  await assert.rejects(fetchJSON('missing.json'),/missing.json: HTTP 404/)
  globalThis.fetch=async()=>({ok:true,json:async()=>{throw new SyntaxError('invalid JSON')}})
  await assert.rejects(fetchJSON('bad.json'),/bad.json: invalid JSON/)
  let signal
  globalThis.fetch=async(_url,options)=>{signal=options.signal;return {ok:true,json:()=>new Promise(()=>{})}}
  await assert.rejects(fetchJSON('stalled.json',undefined,5),/stalled.json: Request timed out/)
  assert.equal(signal.aborted,true)
 } finally {globalThis.fetch=original}
})

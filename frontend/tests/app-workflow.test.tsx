import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import App from '../src/App';
import { api } from '../src/api';
import { DEFAULT_SETTINGS } from '../src/settings';
import { categories, health, job, mockApi, plan, renderUI } from './fixtures';

let stream:any;
class Stream {
 onmessage:any;handlers:Record<string,()=>void>={};close=vi.fn();
 constructor(public url:string){stream=this}
 addEventListener(name:string,fn:()=>void){this.handlers[name]=fn}
}
let seq=0;
function emit(...events:any[]){act(()=>stream.onmessage({data:JSON.stringify(events.map(e=>({seq:seq++,...e})))}))}
const nav=(name:string)=>fireEvent.click(screen.getAllByText(name,{exact:true})[0]);
beforeEach(()=>{
 mockApi();window.history.replaceState({},'','/sort');seq=0;stream=null;
 vi.stubGlobal('EventSource',Stream);
 vi.spyOn(window,'matchMedia').mockImplementation((q)=>({matches:q.includes('reduced-motion'),media:q,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}} as never));
});

it('sorts, reviews, renames, applies and undoes a plan without losing destination data',async()=>{
 renderUI(<App/>);await screen.findByRole('button',{name:'Sort',exact:true});
 await waitFor(()=>expect(api.getSettings).toHaveBeenCalled());
 fireEvent.click(screen.getByRole('button',{name:'Sort',exact:true}));await waitFor(()=>expect(stream).not.toBeNull());
 for(const phase of ['rules','scanning','analyzing','deduplicating','checking','reading','faces','ai']){
  emit({type:'phase',phase});expect(screen.getByRole('button',{name:'Stop',exact:true})).toBeInTheDocument();
 }
 emit({type:'scanned',total:3,source_name:'Trip'},...plan.map(p=>({type:'file',id:p.file_id,kind:p.kind,thumb:p.thumb})),{type:'progress',analyzed:3},{type:'file_error',rel_path:'bad.jpg',error:'bad'}, {type:'context',theme:'A trip',source:'ai'},{type:'warning',message:'One damaged file'}, {type:'categories',categories});
 await screen.findByText('Nature',{exact:true});
 emit(...plan.map(p=>({type:'assign',id:p.file_id,category_id:p.category_id,kind:p.kind})),{type:'done',usage:{calls:2,input_tokens:30,output_tokens:10},warnings:[]});
 await screen.findByRole('button',{name:'Apply · move files'}, {timeout:5000});
 fireEvent.click(screen.getByText('Nature',{exact:true}));
 fireEvent.change(await screen.findByPlaceholderText('Nature'),{target:{value:'Landscapes'}});fireEvent.click(screen.getByRole('button',{name:'Rename folder'}));
 await waitFor(()=>expect(api.renameCategory).toHaveBeenCalledWith('job-one','nature','Landscapes'));
 fireEvent.keyDown(document,{key:'Escape'});nav('Review');expect(await screen.findByText('mountain.jpg')).toBeInTheDocument();nav('Sort');
 fireEvent.click(screen.getByRole('button',{name:'Apply · move files'}));await waitFor(()=>expect(api.apply).toHaveBeenCalledWith('job-one','move'));
 fireEvent.click((await screen.findAllByRole('button',{name:'Undo',exact:true}))[0]);await waitFor(()=>expect(api.undo).toHaveBeenCalledWith('run-one'));
 fireEvent.click(screen.getByRole('button',{name:'Start over'}));expect(screen.getByRole('button',{name:'Sort',exact:true})).toBeInTheDocument();
});

it('surfaces failed starts and allows dismissing and retrying',async()=>{
 vi.mocked(api.startJob).mockRejectedValueOnce(Error('a sort is already running'));
 renderUI(<App/>);await waitFor(()=>expect(api.getSettings).toHaveBeenCalled());fireEvent.click(screen.getByRole('button',{name:'Sort',exact:true}));
 expect(await screen.findByText('Another sort is still running')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Try again'}));await waitFor(()=>expect(stream).not.toBeNull());
 fireEvent.click(screen.getByRole('button',{name:'Stop',exact:true}));await waitFor(()=>expect(api.cancel).toHaveBeenCalledWith('job-one'));
 emit({type:'cancelled'});expect(screen.getByText('Stopped',{exact:true})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Start over'}));fireEvent.click(screen.getByRole('button',{name:'Sort',exact:true}));
 await waitFor(()=>expect(stream).not.toBeNull());emit({type:'error',message:'AI unavailable'});expect(await screen.findByText('AI unavailable')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Dismiss'}));expect(screen.getByRole('button',{name:'Sort',exact:true})).toBeInTheDocument();
});

it('requires an AI key and nonempty instructions for rule sorting',async()=>{
 vi.mocked(api.getSettings).mockResolvedValue({...DEFAULT_SETTINGS,source:'Trip',strategy:'rules'});
 vi.mocked(api.health).mockResolvedValue({...health,ai_available:false});
 renderUI(<App/>);expect(await screen.findByLabelText('Sorting instructions')).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Sorting instructions'),{target:{value:'Landscapes into travel'}});
 expect(screen.getByRole('button',{name:'Sort',exact:true})).toBeDisabled();expect(api.startJob).not.toHaveBeenCalled();
});

it('submits the entered AI instructions and persists them',async()=>{
 vi.mocked(api.getSettings).mockResolvedValue({...DEFAULT_SETTINGS,source:'Trip',strategy:'rules'});
 renderUI(<App/>);fireEvent.change(await screen.findByLabelText('Sorting instructions'),{target:{value:'Landscapes into trip/{date}, others into other/{date}'}});
 fireEvent.click(screen.getByRole('button',{name:'Sort',exact:true}));
 await waitFor(()=>expect(api.startJob).toHaveBeenCalledWith(expect.objectContaining({strategy:'rules',options:expect.objectContaining({rules_prompt:expect.stringContaining('Landscapes')})})));
});

it('navigates every URL tab and applies a chosen category set',async()=>{
 renderUI(<App/>);await waitFor(()=>expect(api.getSettings).toHaveBeenCalled());
 for(const tab of ['Review','Library','Statistics','History','Settings','Categories']){nav(tab);expect(window.location.pathname).toBe('/'+tab.toLowerCase());}
 fireEvent.click((await screen.findAllByRole('button',{name:'Use',exact:true}))[0]);expect(window.location.pathname).toBe('/sort');
 fireEvent.click(screen.getByRole('button',{name:'Quick settings'}));fireEvent.click(await screen.findByRole('button',{name:'All settings →'}));expect(window.location.pathname).toBe('/settings');
 fireEvent.click(screen.getByRole('button',{name:'Change…'}));expect(await screen.findByRole('dialog')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Use this folder'}));await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
 window.history.pushState({},'','/review');fireEvent.popState(window);expect(window.location.pathname).toBe('/review');expect(screen.queryByRole('button',{name:'Apply · move files'})).not.toBeInTheDocument();
});

it.each(['done','applied'])('restores a saved %s plan after reloading',async(status)=>{
 localStorage.setItem('aio.lastJob','job-one');vi.mocked(api.job).mockResolvedValue({...job,status,run_id:status==='applied'?'run-one':null} as never);
 renderUI(<App/>);await waitFor(()=>expect(api.job).toHaveBeenCalledWith('job-one'));
 if(status==='done')expect(await screen.findByRole('button',{name:'Apply · move files'}, {timeout:5000})).toBeInTheDocument();
 else expect(await screen.findByText(/Done. Your files are in/)).toBeInTheDocument();
 nav('Review');expect(await screen.findByText('mountain.jpg')).toBeInTheDocument();
});

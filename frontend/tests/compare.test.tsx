import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ComparePhotos } from '../src/components/ComparePhotos';
import { ReviewTab } from '../src/components/ReviewTab';
import { api } from '../src/api';
import { categories, mockApi, plan, renderUI } from './fixtures';

beforeEach(()=>mockApi());
const photos=()=>plan.slice(0,2).map((p,i)=>({...p,quality:{...p.quality!,aspect_ratio:1.5,faces_considered:1,eyes_open:i?0:1,face_regions:[{box:[.2,.2,.4,.5],sharpness:i?null:.9,blink:i?.9:.1}]}}));

it('compares originals, shows face crops, and synchronizes native-size zoom and pan',async()=>{
 const close=vi.fn();renderUI(<ComparePhotos items={photos()} onClose={close}/>);
 const dialog=await screen.findByRole('dialog');
 expect(within(dialog).getByRole('img',{name:'Face 1 of mountain.jpg'})).toBeInTheDocument();
 fireEvent.click(within(dialog).getByText('100%',{exact:true}));
 const a=screen.getByTestId('comparison-pane-0'),b=screen.getByTestId('comparison-pane-1');
 for(const pane of[a,b]){
  Object.defineProperties(pane,{scrollWidth:{configurable:true,value:1000},clientWidth:{configurable:true,value:200},scrollHeight:{configurable:true,value:800},clientHeight:{configurable:true,value:200}});
 }
 a.scrollLeft=400;a.scrollTop=300;fireEvent.scroll(a);expect(b.scrollLeft).toBe(400);expect(b.scrollTop).toBe(300);
 fireEvent.click(within(dialog).getByText('200%',{exact:true}));expect((within(dialog).getByAltText('mountain.jpg') as HTMLElement).style.zoom).toBe('2');
 fireEvent.click(within(dialog).getByRole('checkbox',{name:'Synchronize pan'}));
 a.scrollLeft=100;fireEvent.scroll(a);expect(b.scrollLeft).toBe(400);
 fireEvent.click(within(dialog).getByRole('checkbox',{name:'Show face regions'}));
 expect(within(dialog).queryByTitle(/check eyes/)).not.toBeInTheDocument();
 fireEvent.click(within(dialog).getByRole('button',{name:'Close',exact:true}));expect(close).toHaveBeenCalledOnce();
});

it('lets a reviewer override the destination in comparison',async()=>{
 const assign=vi.fn().mockResolvedValue(undefined);
 renderUI(<ComparePhotos items={photos()} onClose={()=>{}} categories={categories} onAssign={assign}/>);
 fireEvent.mouseDown(screen.getByRole('combobox',{name:'Destination for mountain.jpg'}));
 fireEvent.click((await screen.findAllByTitle('Food')).at(-1)!);
 await waitFor(()=>expect(assign).toHaveBeenCalledWith('one','food'));
});

it('opens a side-by-side review for selected photos and retains selection after reassignment',async()=>{
 const changed=vi.fn();renderUI(<ReviewTab jobId="j" editable plan={photos()} categories={categories} onChanged={changed}/>);
 expect(screen.getByRole('button',{name:'Compare selected'})).toBeDisabled();
 fireEvent.click(screen.getAllByRole('checkbox')[0]);fireEvent.click(screen.getByRole('button',{name:'Compare selected'}));
 const dialog=await screen.findByRole('dialog');
 fireEvent.mouseDown(within(dialog).getByRole('combobox',{name:'Destination for mountain.jpg'}));
 fireEvent.click((await screen.findAllByTitle('Food')).at(-1)!);
 await waitFor(()=>expect(api.reassign).toHaveBeenCalledWith('j',['one'],'food'));expect(changed).toHaveBeenCalled();
 fireEvent.click(within(dialog).getByRole('button',{name:'Close',exact:true}));
 expect(screen.getByRole('button',{name:'Compare selected'})).toBeEnabled();
});

it('filters close burst decisions, unique views and nondominated alternatives',async()=>{
 const items=photos().map((p,i)=>({...p,burst:{group:1,size:2,best:i===0,margin:.01},pick:{...plan[0].pick!,parts:{novelty:i?.1:.9,pareto:i?0:1}}}));
 renderUI(<ReviewTab jobId="j" editable={false} plan={items} categories={categories} onChanged={()=>{}}/>);
 for(const[label,count]of[['Close burst decisions',2],['Unique views',1],['Alternative strengths',1]]as const){
  fireEvent.mouseDown(screen.getByRole('combobox',{name:'More recommendation filters'}));fireEvent.click(await screen.findByText(label,{exact:true}));
  expect(screen.getByText(`${count} of 2 files`)).toBeInTheDocument();
 }
});

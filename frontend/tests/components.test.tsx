import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../src/api';
import { CategoriesTab } from '../src/components/CategoriesTab';
import { CategoryCard, GhostCard } from '../src/components/CategoryCard';
import { FilesDrawer } from '../src/components/FilesDrawer';
import { FacePicker } from '../src/components/FacePicker';
import { HistoryDrawer } from '../src/components/HistoryDrawer';
import { HistoryTab } from '../src/components/HistoryTab';
import { ReviewTab } from '../src/components/ReviewTab';
import { StatisticsTab } from '../src/components/StatisticsTab';
import { RecipePicker } from '../src/components/RecipePicker';
import { FileDetails } from '../src/components/MediaViewer';
import { categories, history, historyItem, mockApi, plan, presets, recipes, renderUI, run, suggestion } from './fixtures';

beforeEach(()=>mockApi());

it('filters category sets and dispatches use, edit, copy and create actions',()=>{
 const use=vi.fn(),edit=vi.fn();
 renderUI(<CategoriesTab presets={presets} customSets={[{...presets[0],id:'mine',name:'My trip',modified:true}]} activeId="lifestyle" onUse={use} onEdit={edit}/>);
 fireEvent.click(screen.getAllByRole('button',{name:'Use'})[0]);expect(use).toHaveBeenCalledWith(expect.objectContaining({id:'mine'}),true);
 fireEvent.click(screen.getAllByRole('button',{name:'Edit'})[0]);expect(edit).toHaveBeenCalledWith(expect.objectContaining({id:'mine'}),'edit');
 fireEvent.click(screen.getAllByRole('button',{name:'Copy'})[0]);expect(edit).toHaveBeenCalledWith(expect.objectContaining({id:'mine'}),'copy');
 fireEvent.click(screen.getByRole('button',{name:'New category set'}));expect(edit).toHaveBeenCalledWith(null,'new');
 fireEvent.change(screen.getByPlaceholderText(/Find a preset/),{target:{value:'Travel'}});expect(screen.queryByText('Lifestyle',{exact:true})).not.toBeInTheDocument();
});

it('renders folder cards, placeholders and rich file details',()=>{
 const click=vi.fn();renderUI(<><CategoryCard name="Nature" emoji="🌲" count={1} total={2} slotRef={()=>{}} onClick={click} cover="/avatar" tall/><CategoryCard name="Duplicates" count={0} total={0} slotRef={()=>{}} variant="trash"/><GhostCard/><GhostCard name="Pending"/><FileDetails p={plan[0]}/></>);
 fireEvent.click(screen.getByText('Nature',{exact:true}));expect(click).toHaveBeenCalledOnce();
 expect(screen.getByText(/sharp eyes/)).toBeInTheDocument();expect(screen.getByText('Technical 90%')).toBeInTheDocument();expect(screen.getByText(/mountain.xmp/)).toBeInTheDocument();
});

it('renames a folder and opens its video and photo viewers',async()=>{
 const rename=vi.fn().mockResolvedValue(undefined);renderUI(<FilesDrawer title="Nature" items={plan} onClose={()=>{}} onRename={rename}/>);
 fireEvent.change(screen.getByPlaceholderText('Nature'),{target:{value:'Trip'}});fireEvent.click(screen.getByRole('button',{name:'Rename folder'}));
 await waitFor(()=>expect(rename).toHaveBeenCalledWith('Trip'));
 fireEvent.click(screen.getByRole('button',{name:'Open clip.mp4'}));expect(document.querySelector('video')).toHaveAttribute('src',expect.stringContaining('clip.mp4'));
 fireEvent.keyDown(document,{key:'Escape'});fireEvent.click(screen.getByRole('button',{name:'Open mountain.jpg'}));
 await waitFor(()=>expect(screen.getAllByText(/sharp eyes/).length).toBeGreaterThan(0));
 fireEvent.keyDown(document,{key:'ArrowRight'});fireEvent.keyDown(document,{key:'Escape'});
});

it('renders empty drawers without inventing files',()=>{
 renderUI(<FilesDrawer title="Empty" items={[]} onClose={()=>{}}/>);expect(screen.getByText(/Files appear here/)).toBeInTheDocument();
});

it('selects a reference face, uploads another and falls back to everyone',async()=>{
 const change=vi.fn();renderUI(<FacePicker value={null} onChange={change}/>);
 await waitFor(()=>expect(api.faces).toHaveBeenCalled());fireEvent.click(screen.getByText('Only one person'));
 await screen.findByText('Alex');expect(change).toHaveBeenCalledWith('face-one');
 fireEvent.click(screen.getByText('Alex'));fireEvent.keyDown(screen.getByText('Alex').closest('[role="button"]')!,{key:'Enter'});
 fireEvent.change(screen.getByPlaceholderText(/Name \(optional\)/),{target:{value:'Sam'}});
 fireEvent.click(screen.getByRole('button',{name:'Upload face'}));
 fireEvent.change(document.querySelector('input[type=file]')!,{target:{files:[new File(['face'],'face.jpg',{type:'image/jpeg'})]}});
 await waitFor(()=>expect(change).toHaveBeenCalledWith('new-face'));
 fireEvent.click(screen.getByText('Everyone, a folder each'));expect(change).toHaveBeenCalledWith(null);
});

it('forgets a selected reference face and handles empty face libraries',async()=>{
 const change=vi.fn();renderUI(<FacePicker value="face-one" onChange={change}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Forget Alex'}));fireEvent.click(await screen.findByRole('button',{name:'OK'}));
 await waitFor(()=>expect(api.deleteFace).toHaveBeenCalledWith('face-one'));expect(change).toHaveBeenCalledWith(null);
});

it('reviews filters by kind, quality, source, bursts, text and supports sorting',async()=>{
 renderUI(<ReviewTab jobId="j" editable={false} plan={plan} categories={categories} onChanged={()=>{}}/>);
 expect(screen.getByText('3 of 3 files')).toBeInTheDocument();
 for(const [filter,count] of [['Top picks',1],['Unsure',1],['Rejects',1],['Smiling',1],['AI',1],['Bursts',2],['Edited',1],['Everything',3]] as const){
  fireEvent.click(screen.getByText(filter,{exact:true}));expect(screen.getByText(`${count} of 3 files`)).toBeInTheDocument();
 }
 fireEvent.click(screen.getByText('Videos',{exact:true}));expect(screen.getByText('1 of 3 files')).toBeInTheDocument();
 fireEvent.click(screen.getByText('Photos',{exact:true}));expect(screen.getByText('2 of 3 files')).toBeInTheDocument();
 fireEvent.click(screen.getByText('All',{exact:true}));
 fireEvent.change(screen.getByPlaceholderText(/Search file name/),{target:{value:'mountain'}});expect(screen.getByText('1 of 3 files')).toBeInTheDocument();
 fireEvent.change(screen.getByPlaceholderText(/Search file name/),{target:{value:''}});
 for(const name of ['File','Match','Quality','Rating'])fireEvent.click(screen.getAllByText(name,{exact:true})[0]);
});

it('reassigns selected review files to another category',async()=>{
 const changed=vi.fn();renderUI(<ReviewTab jobId="j" editable plan={plan} categories={categories} onChanged={changed}/>);
 fireEvent.click(screen.getAllByRole('checkbox')[1]);
 // The bulk destination selector follows the category filter and row selectors.
 fireEvent.mouseDown(screen.getByText('Move to category…'));fireEvent.click((await screen.findAllByTitle('🥐 Food')).at(-1)!);
 fireEvent.click(screen.getByRole('button',{name:'Move',exact:true}));
 await waitFor(()=>expect(api.reassign).toHaveBeenCalledWith('j',['one'],'food'));expect(changed).toHaveBeenCalled();
});

it('opens a history plan, and filters history outcomes',async()=>{
 const reopen=vi.fn();renderUI(<HistoryTab active onUndone={()=>{}} onReopen={reopen}/>);
 fireEvent.click(await screen.findByRole('button',{name:/Trip.*AI prompt rules/}));
 fireEvent.click(await screen.findByRole('button',{name:'Open this plan'}));expect(reopen).toHaveBeenCalledWith('job-one');
 fireEvent.keyDown(document,{key:'Escape'});fireEvent.click(screen.getByText('Plans',{exact:true}));
 await waitFor(()=>expect(api.history).toHaveBeenLastCalledWith('not_applied',40,0));
});

it('undoes applied history runs and empties recoverable trash explicitly',async()=>{
 const undone=vi.fn();renderUI(<HistoryDrawer open onClose={()=>{}} onUndone={undone}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Empty trash'}));fireEvent.click(await screen.findByRole('button',{name:'Delete forever'}));
 await waitFor(()=>expect(api.emptyTrash).toHaveBeenCalledWith('run-one'));
 fireEvent.click(screen.getByRole('button',{name:'Undo',exact:true}));fireEvent.click(await screen.findByRole('button',{name:'OK'}));
 await waitFor(()=>expect(undone).toHaveBeenCalledWith('run-one'));
});

it('shows performance charts and rows for completed sorts',async()=>{
 renderUI(<StatisticsTab active/>);expect(await screen.findByText('Where the time goes')).toBeInTheDocument();
 expect(screen.getByText('Trip')).toBeInTheDocument();expect(screen.getByText('all succeeded')).toBeInTheDocument();
});

it('shows an actionable empty statistics state',async()=>{
 vi.mocked(api.stats).mockResolvedValue({...mockApi().stats,sorts:0});renderUI(<StatisticsTab active/>);
 expect(await screen.findByText(/No sorts yet/)).toBeInTheDocument();
});

it('recipe recommendations are selectable and all options can be expanded',()=>{
 const pick=vi.fn();renderUI(<RecipePicker recipes={recipes} suggestion={suggestion} loading={false} active="discover" onPick={pick}/>);
 fireEvent.click(screen.getByRole('button',{name:/Not sure: discover/}));expect(pick).toHaveBeenCalledWith(recipes[1]);
 fireEvent.click(screen.getByRole('button',{name:'Show all options'}));expect(screen.getByText('By date')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Fewer options'}));expect(screen.queryByText('By date')).not.toBeInTheDocument();
});

it('sorts folder photos by descending score by default and switches to ascending',async()=>{
 const make=(name:string,score?:number)=>({...plan[0],file_id:name,name,pick:score===undefined?null:{score,reasons:[],picked:false},quality:null});
 renderUI(<FilesDrawer title="Ratings" items={[make('low.jpg',.7),make('high.jpg',.95),make('unknown.jpg'),make('middle.jpg',.8)]} onClose={()=>{}}/>);
 const order=()=>screen.getAllByRole('button',{name:/^Open .*\.jpg$/}).map(b=>b.getAttribute('aria-label'));
 expect(order()).toEqual(['Open high.jpg','Open middle.jpg','Open low.jpg','Open unknown.jpg']);
 fireEvent.mouseDown(screen.getByRole('combobox',{name:'Sort photos by score'}));
 fireEvent.click(await screen.findByText('Score · lowest first'));
 expect(order()).toEqual(['Open low.jpg','Open middle.jpg','Open high.jpg','Open unknown.jpg']);
});

import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { CategoryEditor } from '../src/components/CategoryEditor';
import { FolderPicker, displayPath } from '../src/components/FolderPicker';
import { api } from '../src/api';
import { health, mockApi, presets, renderUI } from './fixtures';

beforeEach(()=>mockApi());

it('creates a category set with named folders, descriptions, media constraints and AI hints',async()=>{
 const saved=vi.fn();vi.mocked(api.saveSet).mockResolvedValue({...presets[0],id:'new',custom:true});
 renderUI(<CategoryEditor open onClose={()=>{}} presets={presets} customSets={[]} onSaved={saved} initial={{set:null,mode:'new'}}/>);
 fireEvent.change(screen.getByPlaceholderText('Set name'),{target:{value:'Travel picks'}});
 fireEvent.change(screen.getByPlaceholderText('Add a short description'),{target:{value:'Favorite trips'}});
 fireEvent.change(screen.getByPlaceholderText('Folder name'),{target:{value:'Mountains'}});
 fireEvent.change(screen.getByLabelText('Icon'),{target:{value:'⛰'}});
 fireEvent.change(screen.getByPlaceholderText(/Only for AI assist/),{target:{value:'Only visible mountains'}});
 fireEvent.click(screen.getByText('Photos',{exact:true}));
 fireEvent.click(screen.getByRole('button',{name:'Add folder'}));fireEvent.change(screen.getByPlaceholderText('Folder name'),{target:{value:'Clips'}});fireEvent.click(screen.getByText('Videos',{exact:true}));
 fireEvent.click(screen.getByRole('button',{name:'Up',exact:true}));fireEvent.click(screen.getByRole('button',{name:'Down',exact:true}));
 fireEvent.click(screen.getByRole('button',{name:'Remove folder'}));
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saved).toHaveBeenCalled());
 expect(api.saveSet).toHaveBeenCalledWith(null,expect.objectContaining({name:'Travel picks',categories:[expect.objectContaining({name:'Mountains',media:'image',ai_hint:'Only visible mountains'})]}));
});

it('validates category names and reports backend save errors',async()=>{
 vi.mocked(api.saveSet).mockRejectedValue(Error('Could not save'));
 renderUI(<CategoryEditor open onClose={()=>{}} presets={presets} customSets={[]} onSaved={()=>{}} initial={{set:presets[0],mode:'copy'}}/>);
 fireEvent.change(screen.getByPlaceholderText('Folder name'),{target:{value:'../bad'}});fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 expect(screen.getAllByText(/Names can’t contain/).length).toBeGreaterThan(0);
 fireEvent.change(screen.getByPlaceholderText('Folder name'),{target:{value:'Food'}});fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));expect(screen.getAllByText(/already called/).length).toBeGreaterThan(0);
 fireEvent.change(screen.getByPlaceholderText('Folder name'),{target:{value:'New category'}});
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));expect(await screen.findByText('Could not save')).toBeInTheDocument();
});

it('deletes a custom set only after confirmation',async()=>{
 const saved=vi.fn();renderUI(<CategoryEditor open onClose={()=>{}} presets={presets} customSets={[{...presets[0],id:'mine'}]} onSaved={saved} initial={{set:{...presets[0],id:'mine'},mode:'edit'}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Delete set'}));fireEvent.click(await screen.findByRole('button',{name:'OK'}));
 await waitFor(()=>expect(api.deleteSet).toHaveBeenCalledWith('mine'));expect(saved).toHaveBeenCalledWith(null);
});

it('browses, filters and chooses a folder with keyboard shortcuts',async()=>{
 const choose=vi.fn();localStorage.setItem('aio.recentFolders',JSON.stringify(['Old trip']));
 vi.mocked(api.folders).mockImplementation(async(path)=>({path,name:path||'Home',media_count:3,folders:[{name:'Holiday',path:'Trip/Holiday',media_count:2,has_children:true}],samples:['Trip/a.jpg']}));
 renderUI(<FolderPicker open value="Trip" health={health} onClose={()=>{}} onChoose={choose}/>);
 expect(await screen.findByText('Holiday')).toBeInTheDocument();
 const filter=screen.getByPlaceholderText(/Filter/);fireEvent.change(filter,{target:{value:'absent'}});expect(screen.queryByText('Holiday')).not.toBeInTheDocument();
 fireEvent.change(filter,{target:{value:''}});fireEvent.keyDown(filter,{key:'ArrowDown'});fireEvent.keyDown(filter,{key:'ArrowUp'});fireEvent.keyDown(filter,{key:'Enter',ctrlKey:true});expect(choose).toHaveBeenCalledWith('Trip/Holiday');
 fireEvent.click(screen.getByRole('button',{name:'Up one folder'}));await waitFor(()=>expect(api.folders).toHaveBeenLastCalledWith(''));
 fireEvent.click(screen.getByText('Pictures'));await waitFor(()=>expect(api.folders).toHaveBeenLastCalledWith('Pictures'));
 fireEvent.doubleClick(screen.getByText('Holiday'));expect(choose).toHaveBeenCalledWith('Trip/Holiday');
});

it('accepts host paths, relative paths and home paths in the folder path bar',async()=>{
 const choose=vi.fn();renderUI(<FolderPicker open value="Trip" health={health} onClose={()=>{}} onChoose={choose}/>);
 await screen.findByText('Holiday');fireEvent.click(screen.getByTitle('Click to type or paste a path'));
 const input=screen.getAllByRole('textbox').find(x=>(x as HTMLInputElement).value==='/photos/Trip')!;
 fireEvent.change(input,{target:{value:'/photos/New/Trip'}});fireEvent.keyDown(input,{key:'Enter'});await waitFor(()=>expect(api.folders).toHaveBeenLastCalledWith('New/Trip'));
 fireEvent.click(screen.getByRole('button',{name:'Use this folder'}));expect(choose).toHaveBeenCalledWith('New/Trip');
 expect(displayPath(null,'Trip')).toBe('/library/Trip');expect(displayPath(health,'')).toBe('/photos');
});

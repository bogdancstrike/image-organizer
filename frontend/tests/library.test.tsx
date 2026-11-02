import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { LibraryTab } from '../src/components/LibraryTab';
import { api } from '../src/api';
import { mockApi, plan, renderUI, wrap } from './fixtures';

const markers=vi.hoisted(()=>[] as Array<()=>void>);
vi.mock('leaflet',()=>({default:{
 latLngBounds:()=>({pad:()=>({})}), map:()=>({fitBounds:vi.fn(),invalidateSize:vi.fn(),remove:vi.fn()}),
 tileLayer:()=>({addTo:vi.fn()}),circleMarker:()=>{const m={bindTooltip:()=>m,on:(_event:string,fn:()=>void)=>{markers.push(fn);return m},addTo:()=>m};return m},
}}));
beforeEach(()=>{mockApi();markers.length=0});
const props={active:true,folder:'Trip',folderLabel:'/photos/Trip',model:'clip' as const,onSortBy:vi.fn()};

it('searches within the chosen folder and browses similar photos',async()=>{
 const view=renderUI(<LibraryTab {...props}/>);
 const input=screen.getByPlaceholderText(/Describe what/);fireEvent.change(input,{target:{value:'mountains'}});fireEvent.click(screen.getByRole('button',{name:'Search',exact:true}));
 await waitFor(()=>expect(api.libSearch).toHaveBeenCalledWith('mountains','Trip','clip'));
 fireEvent.click(await screen.findByTitle(plan[0].rel_path));
 const dialog=await screen.findByRole('dialog');fireEvent.click(within(dialog).getByRole('button',{name:'Next'}));
 expect(within(dialog).getByText(/blur.jpg/)).toBeInTheDocument();fireEvent.keyDown(window,{key:'ArrowLeft'});
 fireEvent.click(within(dialog).getByRole('button',{name:'Find similar'}));await waitFor(()=>expect(api.libSimilar).toHaveBeenCalledWith(plan[0].rel_path,'Trip','clip'));
 fireEvent.click(await screen.findByTitle(plan[0].rel_path));fireEvent.keyDown(document,{key:'Escape'});
 fireEvent.click(screen.getByText('sunset over the sea'));await waitFor(()=>expect(api.libSearch).toHaveBeenLastCalledWith('sunset over the sea','Trip','clip'));
 view.rerender(wrap(<LibraryTab {...props} folder="Other"/>));expect(screen.queryByText('“sunset over the sea”')).not.toBeInTheDocument();
});

it('indexes an unsearchable folder and handles search errors without losing scope',async()=>{
 vi.mocked(api.libStatus).mockResolvedValueOnce({indexed:0}).mockResolvedValue({indexed:3});
 renderUI(<LibraryTab {...props}/>);fireEvent.click(await screen.findByRole('button',{name:'Index this folder'}));
 await waitFor(()=>expect(screen.getByText('Folder indexed. Search away.')).toBeInTheDocument(),{timeout:3000});
 expect(api.startJob).toHaveBeenCalledWith(expect.objectContaining({source:'Trip',strategy:'date'}));
 vi.mocked(api.libSearch).mockRejectedValueOnce(Error('search unavailable'));
 fireEvent.change(screen.getByPlaceholderText(/Describe what/),{target:{value:'mountain'}});fireEvent.click(screen.getByRole('button',{name:'Search',exact:true}));
 expect(await screen.findByText('search unavailable')).toBeInTheDocument();
});

it('shows trips, photo grids and sort-by-trip controls',async()=>{
 vi.mocked(api.libTrips).mockResolvedValue({photos:3,located:3,home:{lat:44,lon:26,city:'Bucharest',country:'Romania'},trips:[{name:'Mountain weekend',count:2,start:100000,end:200000,paths:plan.slice(0,2).map(p=>p.rel_path),samples:[plan[0].rel_path]}]} as never);
 const sort=vi.fn();renderUI(<LibraryTab {...props} onSortBy={sort}/>);fireEvent.click(screen.getByText('Trips',{exact:true}));
 fireEvent.click(await screen.findByRole('button',{name:'Sort into trip folders'}));expect(sort).toHaveBeenCalledWith('trips');
 fireEvent.click(screen.getByText(/Mountain weekend/));fireEvent.click(await screen.findByTitle(plan[0].rel_path));expect(await screen.findByRole('dialog')).toBeInTheDocument();
 fireEvent.keyDown(document,{key:'Escape'});fireEvent.click(screen.getByRole('button',{name:'Close',exact:true}));
});

it('loads geographic groups, maps and country/city sorting actions',async()=>{
 vi.mocked(api.libPlaces).mockResolvedValue({photos:3,located:3,points:[{lat:44,lon:26,count:2,city:'Bucharest',country:'Romania',paths:[plan[0].rel_path]}],countries:[{name:'Romania',count:3}],cities:[]} as never);
 const sort=vi.fn();renderUI(<LibraryTab {...props} onSortBy={sort}/>);fireEvent.click(screen.getByText('Map',{exact:true}));
 fireEvent.click(await screen.findByRole('button',{name:'Sort by country'}));expect(sort).toHaveBeenCalledWith('places',{place_granularity:'country'});
 fireEvent.click(screen.getByRole('button',{name:'Sort by city'}));expect(sort).toHaveBeenCalledWith('places',{place_granularity:'city'});
 await waitFor(()=>expect(markers.length).toBe(1));act(()=>markers[0]());expect(await screen.findByTitle(plan[0].rel_path)).toBeInTheDocument();
 fireEvent.error(screen.getByTitle(plan[0].rel_path).querySelector('img')!);expect(screen.getByTitle(plan[0].rel_path).querySelector('img')).toHaveAttribute('data-fallback','1');
});

it('explains missing GPS and no matching search results',async()=>{
 vi.mocked(api.libSearch).mockResolvedValue({results:[],took_ms:2});renderUI(<LibraryTab {...props}/>);
 fireEvent.change(screen.getByPlaceholderText(/Describe what/),{target:{value:'none'}});fireEvent.click(screen.getByRole('button',{name:'Search',exact:true}));expect(await screen.findByText('No matching photos')).toBeInTheDocument();
 fireEvent.click(screen.getByText('Trips',{exact:true}));expect(await screen.findByText(/No trips found/)).toBeInTheDocument();
 fireEvent.click(screen.getByText('Map',{exact:true}));expect(await screen.findByText(/No photos with GPS/)).toBeInTheDocument();
});

it('filters with stored tags and shows local tag evidence in search and viewer',async()=>{
 const tags=[{label:'mountains',score:.9,group:'scene',source:'local-ai'},{label:'horizontal',score:1,group:'format',source:'metadata'}];
 vi.mocked(api.libTags).mockResolvedValue({tags:[{label:'mountains',count:1},{label:'horizontal',count:2}],tagged:3,indexed:3});
 vi.mocked(api.libSearch).mockResolvedValue({results:[{path:plan[0].rel_path,score:.8,tags,thumb:'/t',captured_at:0}],indexed:3});
 renderUI(<LibraryTab {...props}/>);
 fireEvent.mouseDown(await screen.findByRole('combobox',{name:'Filter image tags'}));fireEvent.click(await screen.findByText('mountains (1)'));
 await waitFor(()=>expect(api.libSearch).toHaveBeenCalledWith('mountains','Trip','clip',['mountains']));
 expect(await screen.findByText('#mountains')).toBeInTheDocument();
 fireEvent.click(screen.getByTitle(plan[0].rel_path));const dialog=await screen.findByRole('dialog');expect(within(dialog).getByText('#mountains')).toBeInTheDocument();
 fireEvent.keyDown(document,{key:'Escape'});fireEvent.click(screen.getByRole('button',{name:'Clear tags'}));
 await waitFor(()=>expect(api.libSearch).toHaveBeenLastCalledWith('mountains','Trip','clip'));
});

it('reports a failed tag refresh instead of saying the folder was indexed',async()=>{
 vi.mocked(api.job).mockResolvedValue({...mockApi().job,status:'error',error:'Cannot read folder'}as never);
 renderUI(<LibraryTab {...props}/>);fireEvent.click(await screen.findByRole('button',{name:'Update search tags'}));
 expect(await screen.findByText('Cannot read folder',{}, {timeout:3000})).toBeInTheDocument();
 expect(screen.queryByText('Folder indexed. Search away.')).not.toBeInTheDocument();
});

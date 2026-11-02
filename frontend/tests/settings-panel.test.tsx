import { useState } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { SettingsPanel, SettingsDrawer } from '../src/components/SettingsDrawer';
import { DEFAULT_SETTINGS, type UiSettings } from '../src/settings';
import { api } from '../src/api';
import { health, mockApi, presets, renderUI } from './fixtures';

beforeEach(()=>mockApi());
function Panel({initial=DEFAULT_SETTINGS,connected=true}:{initial?:UiSettings;connected?:boolean}){
 const [settings,set]=useState(initial);
 return <><SettingsPanel settings={settings} onChange={set} presets={presets} customSets={[{...presets[0],id:'mine',name:'My folders'}]}
 health={{...health,ai_available:connected,faces_available:connected,people_available:connected}} onEditCategories={()=>{}} onPickFolder={()=>{}} gpsAvailable layout="page"/>
 <output data-testid="settings">{JSON.stringify(settings)}</output></>
}
const saved=()=>JSON.parse(screen.getByTestId('settings').textContent!);
const row=(label:string)=>screen.getByText(label,{exact:true}).parentElement!.parentElement!;

it.each(['preset','custom','auto','date','cull','people','trips','places','rules'] as const)('renders and selects the %s organizing mode',async(strategy)=>{
 renderUI(<Panel initial={{...DEFAULT_SETTINGS,strategy,quality:{...DEFAULT_SETTINGS.quality,blur:true,eyes_closed:true,exposure:true,smiles:true,noise_check:true,face_crop:true,tilt_check:true,bursts:true,picks_percent:20,keeper_min_stars:3}}}/>);
 await waitFor(()=>expect(api.aiDefaults).toHaveBeenCalled());
 expect(saved().strategy).toBe(strategy);
 if(strategy==='rules'){
  fireEvent.change(screen.getByLabelText('Sorting instructions'),{target:{value:'Landscapes to trip/{date}'}});expect(saved().rulesPrompt).toContain('Landscapes');
 }else if(strategy==='date'){
  fireEvent.click(screen.getByText('Day',{exact:true}));expect(saved().dateGranularity).toBe('day');
 }else if(strategy==='auto'){
  fireEvent.click(screen.getByText('Fine',{exact:true}));expect(saved().granularity).toBe('fine');
 }else if(strategy==='people'){
  fireEvent.click(screen.getByText('A copy for every person'));expect(saved().peopleMulti).toBe('copy');
 }else if(strategy==='places'){
  fireEvent.click(screen.getByText('City',{exact:true}));expect(saved().placeGranularity).toBe('city');
 }
});

it('persists quality, duplicate, output, and AI settings through user interactions',async()=>{
 renderUI(<Panel/>);
 fireEvent.click(within(row('Separate Photos/ and Videos/')).getByRole('switch'));expect(saved().splitMedia).toBe(false);
 fireEvent.click(screen.getByText('Directly in the folder'));expect(saved().outputMode).toBe('direct');
 fireEvent.click(screen.getByText('In a subfolder'));fireEvent.change(screen.getByPlaceholderText('Organized'),{target:{value:'Albums'}});expect(saved().outputDir).toBe('Albums');
 fireEvent.click(screen.getByText('Only this folder'));expect(saved().recursive).toBe(false);
 fireEvent.click(screen.getByText('This folder + all subfolders'));expect(saved().recursive).toBe(true);
 for(const label of [/Blurry \/ out of focus/,/Eyes closed/,/Smiles \(tag\)/,/Too dark \/ too bright/,/Noisy \(high ISO\)/,/Face cut off by the frame/,/Tilted horizon \(beta\)/,/Best of burst/]){
  fireEvent.click(screen.getByText(label).closest('label')!.querySelector('[role=switch]')!);
 }
 expect(saved().quality.enabled).toBe(true);expect(saved().quality.blur).toBe(true);
 fireEvent.click(screen.getByText('Main subject only'));expect(saved().quality.faces_rule).toBe('main');
 fireEvent.click(screen.getByText('Only tag them'));expect(saved().quality.action).toBe('tag');
 fireEvent.click(within(row('Also group similar shots taken at any time')).getByRole('switch'));expect(saved().quality.similar_any_time).toBe(true);
 fireEvent.click(screen.getByText(/Write ratings to XMP on Apply/).closest('label')!.querySelector('[role=switch]')!);expect(saved().quality.write_xmp).toBe(true);
 fireEvent.click(screen.getByText(/Delete \(recoverable trash\)/));expect(saved().duplicatesAction).toBe('delete');
 fireEvent.click(screen.getByText('Copy files'));expect(saved().applyMode).toBe('copy');
 fireEvent.click(within(row('AI assist')).getByRole('switch'));expect(saved().aiAssist).toBe(true);
 fireEvent.click(screen.getByText('High',{exact:true}));expect(saved().ai.reasoning_effort).toBe('high');
 fireEvent.click(screen.getByText('Every photo (most accurate)'));expect(saved().ai.assist_scope).toBe('all');
 await screen.findByDisplayValue('Name {groups}');
 fireEvent.change(screen.getByDisplayValue('Name {groups}'),{target:{value:'Name in Romanian'}});expect(saved().ai.naming_prompt).toBe('Name in Romanian');
 fireEvent.click(screen.getByText('reset to default'));expect(saved().ai.naming_prompt).toBe('');
 fireEvent.click(screen.getByText('Light',{exact:true}));expect(document.documentElement.dataset.theme).toBe('light');
 const clipboard=vi.fn().mockResolvedValue(undefined);Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:clipboard}});
 fireEvent.click(screen.getByRole('button',{name:'Copy',exact:true}));expect(clipboard).toHaveBeenCalledWith(expect.stringContaining('Albums'));
 fireEvent.click(screen.getByRole('button',{name:'Reset',exact:true}));fireEvent.click(await screen.findByRole('button',{name:'OK'}));expect(saved().source).toBe('');expect(saved().outputDir).toBe('Organized');
});

it('handles disabled engines and requires exact text before deleting application data',async()=>{
 vi.mocked(api.factoryReset).mockRejectedValue(Error('A sort is running'));
 renderUI(<Panel initial={{...DEFAULT_SETTINGS,strategy:'people'}} connected={false}/>);
 expect(screen.getByText(/Face model not found/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Delete all data…'}));
 const submit=await screen.findByRole('button',{name:'I understand, delete everything',exact:true});expect(submit).toBeDisabled();
 fireEvent.change(screen.getByPlaceholderText('delete all data'),{target:{value:'wrong'}});expect(submit).toBeDisabled();
 fireEvent.change(screen.getByPlaceholderText('delete all data'),{target:{value:'delete all data'}});
 fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(submit);
 expect(await screen.findByText('A sort is running')).toBeInTheDocument();expect(api.factoryReset).toHaveBeenCalledWith('delete all data',true);
 fireEvent.keyDown(document,{key:'Escape'});
});

it('quick settings links to the full settings page',async()=>{
 const all=vi.fn();renderUI(<SettingsDrawer open onClose={()=>{}} onOpenAll={all} settings={DEFAULT_SETTINGS} onChange={()=>{}} presets={presets} customSets={[]} health={health} onEditCategories={()=>{}} onPickFolder={()=>{}}/>);
 fireEvent.click(await screen.findByRole('button',{name:'All settings →'}));expect(all).toHaveBeenCalledOnce();
});

it('adjusts numeric thresholds, recommendation profile and generation settings',async()=>{
 renderUI(<Panel initial={{...DEFAULT_SETTINGS,strategy:'cull',quality:{...DEFAULT_SETTINGS.quality,blur:true,eyes_closed:true,smiles:true,exposure:true,noise_check:true,tilt_check:true,bursts:true,picks_percent:20,keeper_min_stars:3}}}/>);
 for(const slider of screen.getAllByRole('slider'))fireEvent.keyDown(slider,{key:'ArrowRight',keyCode:39,which:39});
 expect(saved().quality.blur_threshold).toBeGreaterThan(DEFAULT_SETTINGS.quality.blur_threshold);
 fireEvent.mouseDown(screen.getByRole('combobox',{name:'Recommendation profile'}));
 fireEvent.click(await screen.findByText('Fashion / modeling · pose, styling, light'));expect(saved().quality.pick_profile).toBe('fashion');
 for(const numeric of screen.getAllByRole('spinbutton'))fireEvent.change(numeric,{target:{value:'15'}});
 await screen.findByDisplayValue('Sort {count}');fireEvent.change(screen.getByDisplayValue('Sort {count}'),{target:{value:'Sort carefully'}});expect(saved().ai.assist_prompt).toBe('Sort carefully');
 fireEvent.click(screen.getByText('System',{exact:true,selector:'button'}));expect(HTMLElement.prototype.scrollIntoView).toHaveBeenCalled();
});

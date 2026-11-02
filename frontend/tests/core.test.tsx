import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { api, previewUrl, subscribe, thumbUrl } from '../src/api';
import { DEFAULT_SETTINGS, loadSettings, migrateSettings, saveSettings } from '../src/settings';
import { cn, fmt, prefersReducedMotion } from '../src/lib/utils';
import { LangProvider, useI18n } from '../src/i18n';
import { ThemeRoot, ThemeSwitcher, useTheme } from '../src/theme';
import { PromptRulesInput } from '../src/components/PromptRulesInput';
import { CountUp } from '../src/components/CountUp';
import { Flower } from '../src/components/Flower';

it('migrates old quality settings and preserves current settings safely', () => {
  expect(loadSettings()).toEqual(DEFAULT_SETTINGS);
  localStorage.setItem('aio.settings.v1','broken'); expect(loadSettings()).toEqual(DEFAULT_SETTINGS);
  const settings=migrateSettings({source:'Trip',rulesPrompt:'landscapes to trip',quality:{enabled:true} as never});
  expect(settings.quality.enabled).toBe(false);
  saveSettings({...settings,qualityVersion:2,quality:{...settings.quality,blur:true}});
  expect(loadSettings().quality.blur).toBe(true);
  expect(loadSettings().rulesPrompt).toContain('landscapes');
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('full')});
  expect(()=>saveSettings(settings)).not.toThrow();
});

it('formats counts and merges conflicting class names',()=>{
  expect(fmt(10000)).toBe('10,000');expect(cn('p-1',false,'p-4')).toBe('p-4');expect(prefersReducedMotion()).toBe(false);
});

it('persists language choice and translates prompt-rule instructions',()=>{
  function Probe(){const {t,setLang}=useI18n();return <button onClick={()=>setLang('ro')}>{t('rules.title')} {t('recipe.counts',{photos:2,videos:1})}</button>}
  render(<LangProvider><Probe/></LangProvider>);
  fireEvent.click(screen.getByRole('button'));
  expect(screen.getByText(/Reguli AI/)).toBeInTheDocument();expect(localStorage.getItem('aio.lang')).toBe('ro');
});

it('switches themes and renders an accessible rules textarea',()=>{
  function Probe(){const {theme}=useTheme();return <span>{theme}</span>}
  const change=vi.fn();
  render(<ThemeRoot><LangProvider><ThemeSwitcher/><Probe/><PromptRulesInput value="" onChange={change} aiAvailable={false}/></LangProvider></ThemeRoot>);
  fireEvent.click(screen.getByRole('radio',{name:'Light'}));expect(document.documentElement.dataset.theme).toBe('light');
  expect(localStorage.getItem('aio.theme')).toBe('light');
  fireEvent.change(screen.getByLabelText('Sorting instructions'),{target:{value:'mountains to trips/{date}'}});
  expect(change).toHaveBeenCalledWith('mountains to trips/{date}');expect(screen.getByText(/Set OPENAI_API_KEY/)).toBeInTheDocument();
});

it('animates counts to the requested value and renders the aperture caption',()=>{
  vi.useFakeTimers();const {rerender}=render(<CountUp value={2}/>);rerender(<CountUp value={1200}/>);
  act(()=>vi.advanceTimersByTime(600));expect(screen.getByText('1,200')).toBeInTheDocument();
  render(<Flower caption="sorted"/>);expect(screen.getByText('sorted')).toBeInTheDocument();
});

it('encodes preview URLs and exercises API methods with their correct HTTP verbs',async()=>{
  const fetcher=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response('{}',{headers:{'content-type':'application/json'}}));
  // Response bodies can only be consumed once, so each request gets a fresh response.
  fetcher.mockImplementation(async()=>new Response('{}',{headers:{'content-type':'application/json'}}));
  expect(thumbUrl('Trip/a b.jpg')).toContain('Trip%2Fa%20b.jpg');expect(previewUrl('x/y')).toContain('x%2Fy');
  await api.health();await api.presets();await api.sets();await api.saveSet(null,{name:'Trip',categories:[]});
  await api.saveSet('mine',{name:'Trip',categories:[]});await api.deleteSet('mine');await api.folders('a/b');
  await api.startJob({strategy:'rules',source:'Trip',set_id:null,options:{rules_prompt:'photos to trip'} as never});
  await api.job('j');await api.cancel('j');await api.apply('j','copy');await api.reassign('j',['f'],'c');
  await api.history('all',20,0);await api.emptyTrash('r');await api.libStatus('Trip','clip');await api.libSearch('mountains','Trip','clip');
  await api.libSimilar('a.jpg','Trip','clip');await api.libPlaces('Trip');await api.libTrips('Trip');
  await api.factoryReset('delete all data',false);await api.places();await api.faces();await api.addFace(new File(['x'],'face.jpg',{type:'image/jpeg'}),'Someone');
  await api.deleteFace('f');await api.stats();await api.getSettings();await api.putSettings(DEFAULT_SETTINGS);await api.recipes();await api.suggest('Trip',true);
  await api.renameCategory('j','c','Mountains');await api.aiDefaults();await api.aiModels();await api.runs();await api.undo('r');
  expect(fetcher).toHaveBeenCalledWith('/api/jobs/j/apply',expect.objectContaining({method:'POST',body:JSON.stringify({mode:'copy'})}));
});

it.each([['{"detail":"no access"}','no access'],['oops','403 Forbidden']])('reports API errors: %s',async(body,message)=>{
 vi.spyOn(globalThis,'fetch').mockImplementation(async()=>new Response(body,{status:403,statusText:'Forbidden'}));
 await expect(api.health()).rejects.toThrow(message);await expect(api.addFace(new File(['x'],'x'),'name')).rejects.toThrow(message);
});

it('handles no-content responses and SSE batches, malformed messages, and closing',async()=>{
 vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(null,{status:204}));expect(await api.deleteSet('x')).toBeUndefined();
 let es:any;class Source{onmessage:any;handlers:any={};close=vi.fn();constructor(public url:string){es=this}addEventListener(k:string,cb:unknown){this.handlers[k]=cb}}
 vi.stubGlobal('EventSource',Source);const events=vi.fn(),end=vi.fn();const stop=subscribe('j',events,end);
 es.onmessage({data:'bad'});expect(events).not.toHaveBeenCalled();
 es.onmessage({data:JSON.stringify({type:'phase',phase:'scanning'})});expect(events).toHaveBeenCalledWith([{type:'phase',phase:'scanning'}]);
 es.onmessage({data:'[]'});es.handlers.end();expect(end).toHaveBeenCalledOnce();stop();expect(es.close).toHaveBeenCalledTimes(2);
});

it('migrates legacy keeper stars to the visible decimal threshold',()=>{
 const migrated=migrateSettings({qualityVersion:2,quality:{...DEFAULT_SETTINGS.quality,keeper_min_rating:undefined,keeper_min_stars:3} as never});
 expect(migrated.quality.keeper_min_rating).toBe(3);expect(migrated.quality.pick_min_rating).toBe(4.5);
 expect(migrated.quality.keeper_min_stars).toBe(0);
});

it('encodes tag filters as separate query parameters',async()=>{
 const fetcher=vi.spyOn(globalThis,'fetch').mockImplementation(async()=>new Response('{}',{status:200}));
 await api.libTags('Trip','siglip2');await api.libSearch('red dress','Trip','siglip2',['red','dress']);
 expect(fetcher).toHaveBeenLastCalledWith(expect.stringContaining('tag=red&tag=dress'),expect.anything());
});

it('explains status and model tags consistently',async()=>{
 const {tagExplanation,badgeText}=await import('../src/components/PhotoBadge');
 for(const [label,part]of[['AI assist','OpenAI'],['AI names','names'],['connected · test','key'],['off · no OPENAI_API_KEY','unavailable'],['CPU','CPU'],['NVIDIA GPU','GPU'],['CLIP · local','embedding'],['built-in','preset'],['edited','changes'],['in use','selected'],['mine','custom'],['undone','reversed'],['unknown','Status']]){
  expect(tagExplanation(label)).toContain(part);
 }
 expect(badgeText(<span>Local <b>tags</b></span>)).toBe('Local tags');
});

it('migrates the removed duplicate-trash choice to a Duplicates folder',()=>{
 expect(migrateSettings({duplicatesAction:'delete'} as any).duplicatesAction).toBe('folder');
});

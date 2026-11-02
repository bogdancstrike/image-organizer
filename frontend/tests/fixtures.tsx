import { render } from '@testing-library/react';
import { vi } from 'vitest';
import type { ReactNode } from 'react';
import { ThemeRoot } from '../src/theme';
import { LangProvider } from '../src/i18n';
import { DEFAULT_SETTINGS } from '../src/settings';
import { api, type PlanItem } from '../src/api';

export const presets=[{id:'lifestyle',name:'Lifestyle',description:'Everyday photos',categories:[
 {id:'nature',name:'Nature',emoji:'🌲',prompts:['landscape'],media:'image' as const},
 {id:'food',name:'Food',emoji:'🥐',prompts:['food'],media:'any' as const},
 {id:'video',name:'Clips',emoji:'🎬',prompts:['video'],media:'video' as const}]},
 {id:'boudoir',name:'Boudoir & glamour',description:'A photo session',categories:[{id:'portrait',name:'Portraits',prompts:['portrait']}]},
 {id:'travel',name:'Travel',categories:[{id:'city',name:'Cities',prompts:['city']}]}];
export const recipes=[{id:'boudoir',emoji:'🖤',strategy:'preset' as const,set_id:'boudoir',options:{}},
 {id:'discover',emoji:'✨',strategy:'auto' as const,options:{focus:'auto'}},
 {id:'photoshoot',emoji:'📸',strategy:'cull' as const,options:{}},
 {id:'by-date',emoji:'📆',strategy:'date' as const,options:{}},
 {id:'people',emoji:'👤',strategy:'people' as const,options:{}},
 {id:'camera-roll',emoji:'📷',strategy:'preset' as const,set_id:'lifestyle',options:{}}];
export const health={status:'ok',version:'0.1.0',ai_available:true,model:'test-model',library_ok:true,library_name:'Photos',library_host_path:'/photos',faces_available:true,people_available:true,ocr_available:true,models:['clip','siglip2'],output_dir:'Organized',device:'cpu'};
export const suggestion={photos:3,videos:1,gps_share:0,suggestions:[{recipe:'boudoir',reason:{key:'theme',theme:'Studio',pct:90}}]};
export const plan:PlanItem[]=[
 {file_id:'one',rel_path:'Trip/mountain.jpg',name:'mountain.jpg',kind:'image',thumb:'/thumb/one',category_id:'nature',category:'Nature',confidence:.9,source:'ai',destination:'Trip/Organized/Nature',duplicate_of:null,sidecars:['Trip/mountain.xmp'],quality:{score:.9,stars:5,sharpness:.95,brightness:.5,faces:1,blink:.1,smile:.9,flags:[],smiling:true,faces_checked:true},burst:{group:1,size:3,best:true},pick:{picked:true,score:.9,reasons:['sharp eyes']}},
 {file_id:'two',rel_path:'Trip/blur.jpg',name:'blur.jpg',kind:'image',thumb:'/thumb/two',category_id:'food',category:'Food',confidence:.2,source:'clip',destination:'Trip/Organized/Food',duplicate_of:null,sidecars:[],quality:{score:.2,stars:1,sharpness:.2,brightness:.1,faces:2,blink:.9,smile:0,flags:['blurry','eyes-closed'],smiling:false,faces_checked:true},burst:{group:1,size:3,best:false}},
 {file_id:'three',rel_path:'Trip/clip.mp4',name:'clip.mp4',kind:'video',thumb:'/thumb/three',category_id:'video',category:'Clips',confidence:1,source:'manual',destination:'Trip/Organized/Clips',duplicate_of:null,sidecars:[],quality:null,burst:null},
];
export const categories=presets[0].categories.map(c=>({...c,photos:c.id==='video'?0:1,videos:c.id==='video'?1:0}));
export const job={id:'job-one',request:{source:'Trip',strategy:'preset'},status:'done',phase:'done',categories,plan,
 stats:{total:3,photos:2,videos:1,analyzed:3,folders:3,duplicates:0},warnings:[],errors:[],usage:null,context:null,run_id:null,error:null};
export const run={run_id:'run-one',job_id:'job-one',created_at:new Date().toISOString(),mode:'move',moved:3,failed:0,status:'applied',source:'Trip',in_trash:1};
export const historyItem={job_id:'job-one',source:'Trip',strategy:'rules',model:'clip',finished_at:Date.now()/1000,files:3,photos:2,videos:1,folders:3,duplicates:1,wall:4,phases:{scanning:.1,analyzing:3.9},usage:{input_tokens:10,output_tokens:5},outcome:'not_applied',run:null,categories:[{name:'Nature',count:2}],reopen:true};
export const history={items:[historyItem],total:1,counts:{all:1,applied:0,undone:0,not_applied:1,cancelled:0,failed:0},limit:40,offset:0};
export function wrap(node:ReactNode){return <ThemeRoot><LangProvider>{node}</LangProvider></ThemeRoot>}
export function renderUI(node:ReactNode){return render(wrap(node))}
export function mockApi(){
 const values:any={health,presets,sets:[],getSettings:{...DEFAULT_SETTINGS,source:'Trip',recipeFor:'Trip'},putSettings:{ok:true},recipes,suggest:suggestion,
  aiDefaults:{naming_prompt:'Name {groups}',assist_prompt:'Sort {count}',naming_placeholders:['{groups}'],assist_placeholders:['{count}'],naming_format:'JSON',assist_format:'JSON'},aiModels:{models:['test-model']},
  places:[{id:'pictures',name:'Pictures',path:'Pictures'}],folders:{path:'Trip',name:'Trip',media_count:3,folders:[{name:'Holiday',path:'Trip/Holiday',media_count:2,has_children:false}],samples:[]},
  faces:[{id:'face-one',name:'Alex',cover:null,faces_in_photo:1}],libStatus:{indexed:3},libSearch:{results:plan.slice(0,2).map(p=>({path:p.rel_path,score:.9})),took_ms:10},libSimilar:{results:[{path:plan[0].rel_path,score:1}]},
  libPlaces:{photos:3,located:0,points:[],countries:[],cities:[]},libTrips:{photos:3,located:0,trips:[],home:null},history,runs:[run],job,startJob:{id:'job-one'},apply:{run_id:'run-one',moved:3,failed:[],skipped:0},undo:{run_id:'run-one',status:'undone',undo:{restored:3,problems:[]}},
  emptyTrash:{deleted:1,freed_bytes:1000},renameCategory:{categories,plan},reassign:{changed:[{...plan[0],category_id:'food',category:'Food'}],categories,stats:job.stats},factoryReset:{ok:true},addFace:{id:'new-face',name:'Sam',cover:'/thumb/new',faces_in_photo:2},
  stats:{sorts:1,failed_sorts:0,files_processed:3,files_analyzed:3,photos_organized:0,applies:0,processing_seconds:4,avg_seconds_per_sort:4,avg_files_per_second:.75,ai_tokens:0,phase_seconds:{scanning:.1,analyzing:3.9},by_strategy:{rules:1},by_model:{clip:1},recent:[{...historyItem,status:'done',embedded:3}]}};
 for(const key of Object.keys(api))vi.spyOn(api,key as keyof typeof api).mockResolvedValue(values[key] as never);
 return values;
}

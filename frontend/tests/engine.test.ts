import { expect, it, vi } from 'vitest';
import { SortEngine } from '../src/anim/engine';

function engine(available=true){
 let now=0,id=0;const callbacks=new Map<number,FrameRequestCallback>();
 vi.spyOn(performance,'now').mockImplementation(()=>now);
 vi.spyOn(globalThis,'requestAnimationFrame').mockImplementation(cb=>{callbacks.set(++id,cb);return id});
 vi.spyOn(globalThis,'cancelAnimationFrame').mockImplementation(i=>{callbacks.delete(i)});
 vi.spyOn(globalThis,'Image').mockImplementation(class { naturalWidth=100;naturalHeight=80;onload?:()=>void;set src(_v:string){this.onload?.()} } as never);
 const stage=document.createElement('div'),pile=document.createElement('div'),slot=document.createElement('div');
 stage.getBoundingClientRect=()=>({left:0,top:0,width:600,height:400} as DOMRect);
 pile.getBoundingClientRect=()=>({left:200,top:100,width:200,height:200} as DOMRect);
 slot.getBoundingClientRect=()=>({left:20,top:50,width:150,height:50} as DOMRect);
 const landed=vi.fn();const canvas=document.createElement('canvas');
 const model=new SortEngine(canvas,{stage:()=>stage,pile:()=>pile,slotArea:()=>available?slot:null,onLand:landed});
 const advance=(ms:number)=>{for(let n=0;n<ms;n+=16){now+=16;const frame=[...callbacks.values()];callbacks.clear();for(const cb of frame)cb(now)}};
 return {model,landed,advance,canvas};
}

it('animates real thumbnail flights into folder slots and resets without pending work',()=>{
 const {model,landed,advance,canvas}=engine();model.setExpected(3);model.setWobble(true);model.expectAssigns(3);
 model.addFile('a','/a');model.addFile('a','/a');model.addFile('b','/b');model.addFile('c','/c');model.refreshTheme();
 model.assign('a','folder');model.assign('b','folder');model.assign('c','folder');expect(model.pendingFlights).toBe(3);
 advance(4000);expect(landed).toHaveBeenCalledTimes(3);expect(model.pendingFlights).toBe(0);expect(canvas.width).toBe(600);
 model.reset();expect(model.pendingFlights).toBe(0);advance(20);model.destroy();
});

it('reduced motion snaps assignments directly into cards',()=>{
 const {model,landed,advance}=engine();model.reduced=true;model.expectAssigns(1);model.addFile('a','/a');model.assign('a','folder');advance(40);
 expect(landed).toHaveBeenCalledWith('folder','a');model.destroy();
});

it('a missing folder cannot stall every remaining assignment indefinitely',()=>{
 const {model,landed,advance}=engine(false);model.expectAssigns(1);model.addFile('a','/a');model.assign('a','missing');advance(4000);
 expect(landed).toHaveBeenCalledWith('missing','a');expect(model.pendingFlights).toBe(0);model.destroy();
});

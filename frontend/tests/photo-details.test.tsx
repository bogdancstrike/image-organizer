import { fireEvent, screen, waitFor } from '@testing-library/react';
import { expect, it } from 'vitest';
import { PhotoInfoPanel, useMediaViewer } from '../src/components/MediaViewer';
import { plan, renderUI, wrap } from './fixtures';

it('shows recommendation scores, reasons, tags and trash evidence in a persistent panel',()=>{
 const photo={...plan[0],destination:'.aio-trash/run',tags:[{label:'portrait',score:.9,group:'style',source:'local-ai'}],
  quality:{...plan[0].quality!,faces_considered:1,eyes_open:1,flags:['blurry']},
  decision:{action:'recoverable-trash',explanation:'A duplicate was set aside.',evidence:['An identical file was kept.'],kept_path:'kept.jpg',previous:{category:'Nature',explanation:'Previously suggested category.'}}};
 renderUI(<PhotoInfoPanel p={photo}/>);
 expect(screen.getByRole('complementary',{name:'Photo recommendations'})).toBeInTheDocument();
 expect(screen.getByText('Recoverable trash')).toBeInTheDocument();expect(screen.getByText('4.60')).toBeInTheDocument();
 expect(screen.getByRole('progressbar',{name:'Technical quality'})).toHaveAttribute('aria-valuenow','90');
 expect(screen.getByText('sharp eyes')).toBeInTheDocument();expect(screen.getByText('An identical file was kept.')).toBeInTheDocument();
 expect(screen.getByText(/Kept original.*kept.jpg/)).toBeInTheDocument();expect(screen.getByText(/Previous suggestion.*Nature/)).toBeInTheDocument();
 expect(screen.getByText('#portrait')).toBeInTheDocument();expect(screen.getByText(/eyes open on 1\/1/)).toBeInTheDocument();
});

it('handles unscored and duplicate photos without inventing ratings',()=>{
 renderUI(<PhotoInfoPanel p={{...plan[0],pick:null,quality:null,duplicate_of:'original',sidecars:[],source:'unknown'}}/>);
 expect(screen.getByText('A duplicate matcher selected another file to keep.')).toBeInTheDocument();
 expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();expect(screen.queryByText(/\/ 5/)).not.toBeInTheDocument();
});

it('explains artifact strengths and handles future score components safely',()=>{
 renderUI(<PhotoInfoPanel p={{...plan[0],pick:{...plan[0].pick!,parts:{blocking:1.4,custom:.3,invalid:NaN}},quality:{...plan[0].quality!,flags:[]}}}/>);
 expect(screen.getByRole('progressbar',{name:'Block artifacts'})).toHaveAttribute('aria-valuenow','100');
 expect(screen.getByRole('progressbar',{name:'custom'})).toHaveAttribute('aria-valuenow','30');
 expect(screen.queryByRole('progressbar',{name:'invalid'})).not.toBeInTheDocument();
 expect(screen.getByText(/No enabled quality checks/)).toBeInTheDocument();
});

it('keeps full-screen recommendations beside the image and follows photo navigation',async()=>{
 function Viewer(){const viewer=useMediaViewer(plan.slice(0,2));return <><button onClick={()=>viewer.open(plan[0])}>Open full screen</button>{viewer.node}</>}
 renderUI(<Viewer/>);fireEvent.click(screen.getByRole('button',{name:'Open full screen'}));
 expect(await screen.findByRole('complementary',{name:'Photo recommendations'})).toHaveTextContent('mountain.jpg');
 expect(screen.getByLabelText('Photo preview')).toBeInTheDocument();
 fireEvent.keyDown(window,{key:'ArrowRight',keyCode:39,which:39});
 await waitFor(()=>expect(screen.getByRole('complementary',{name:'Photo recommendations'})).toHaveTextContent('blur.jpg'));
 fireEvent.keyDown(window,{key:'Escape'});
 await waitFor(()=>expect(screen.queryByRole('complementary',{name:'Photo recommendations'})).not.toBeInTheDocument());
});

it('does not open full-screen review when a new winner arrives in the plan',async()=>{
 function Viewer({items}:{items:typeof plan}){const viewer=useMediaViewer(items);return <><button onClick={()=>viewer.open(items[0])}>View winner</button>{viewer.node}</>}
 const view=renderUI(<Viewer items={[]}/>);view.rerender(wrap(<Viewer items={plan.slice(0,1)}/>));
 await waitFor(()=>expect(screen.queryByRole('complementary',{name:'Photo recommendations'})).not.toBeInTheDocument());
 fireEvent.click(screen.getByRole('button',{name:'View winner'}));expect(await screen.findByRole('complementary',{name:'Photo recommendations'})).toBeInTheDocument();
});

it('omits the generic quality-assignment sentence while retaining concrete evidence',()=>{
 renderUI(<PhotoInfoPanel p={{...plan[0],source:'quality',decision:{action:'recommend',explanation:'Assigned by photo quality checks and recommendation ratings.',evidence:['Recommendation 4.60/5; Picks ≥4.5/5.']}}}/>);
 expect(screen.queryByText('Assigned by photo quality checks and recommendation ratings.')).not.toBeInTheDocument();
 expect(screen.getByText('Recommendation 4.60/5; Picks ≥4.5/5.')).toBeInTheDocument();
 expect(screen.getByRole('progressbar',{name:'Technical quality'})).toBeInTheDocument();
 expect(screen.getByText('sharp eyes')).toBeInTheDocument();
});

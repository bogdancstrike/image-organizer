import { useRef, useState } from "react";
import { Checkbox, Modal, Segmented, Select } from "antd";
import { previewUrl, type JobCategory, type PlanItem } from "@/api";
import { FileDetails } from "./MediaViewer";

/** Survey two to four originals with synchronized native-size zoom and normalized scroll positions. */
export function ComparePhotos({ items, onClose, categories = [], onAssign }: {
  items: PlanItem[]; onClose: () => void; categories?: JobCategory[];
  onAssign?: (id: string, category: string) => Promise<void>;
}) {
  const [zoom, setZoom] = useState("fit");
  const [sync, setSync] = useState(true);
  const [faces, setFaces] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const panes = useRef<(HTMLDivElement | null)[]>([]);
  const scrolling = useRef(false);
  const scroll = (index: number) => {
    if (!sync || scrolling.current) return;
    const source = panes.current[index]; if (!source) return;
    scrolling.current = true;
    const x = source.scrollLeft / Math.max(1, source.scrollWidth-source.clientWidth);
    const y = source.scrollTop / Math.max(1, source.scrollHeight-source.clientHeight);
    panes.current.forEach((pane, i) => {
      if (pane && i !== index) { pane.scrollLeft=x*(pane.scrollWidth-pane.clientWidth); pane.scrollTop=y*(pane.scrollHeight-pane.clientHeight); }
    });
    requestAnimationFrame(()=>{ scrolling.current = false; });
  };
  return <Modal open={items.length >= 2} title="Compare photos" onCancel={onClose} footer={null} width="min(1500px, 96vw)" destroyOnHidden>
    <div className="mb-3 flex flex-wrap items-center gap-4 text-xs">
      <Segmented aria-label="Comparison zoom" value={zoom} onChange={setZoom} options={[{value:"fit",label:"Fit"},{value:"100",label:"100%"},{value:"200",label:"200%"}]} />
      <Checkbox checked={sync} onChange={e=>setSync(e.target.checked)}>Synchronize pan</Checkbox>
      <Checkbox checked={faces} onChange={e=>setFaces(e.target.checked)}>Show face regions</Checkbox>
      <span className="text-plum/55">100% uses original image pixels. Scroll to inspect focus; originals are unchanged.</span>
    </div>
    <div className={`grid gap-3 ${items.length > 2 ? "grid-cols-1 md:grid-cols-2 xl:grid-cols-4" : "grid-cols-1 md:grid-cols-2"}`}>
      {items.slice(0,4).map((p, index)=><div key={p.file_id} className="min-w-0 rounded-xl border border-line p-2">
        <div ref={el=>{panes.current[index]=el;}} onScroll={()=>scroll(index)} data-testid={`comparison-pane-${index}`}
          className="h-[50vh] overflow-auto rounded-lg bg-black/90">
          <div className="relative inline-block align-top" style={{maxWidth:zoom==="fit"?"100%":undefined}}>
            <img src={previewUrl(p.preview_path ?? p.rel_path)} alt={p.name} className={zoom==="fit"?"block max-h-[50vh] max-w-full":"block max-w-none"}
              style={zoom==="200"?{zoom:2}:undefined} />
            {faces && p.quality?.face_regions?.map((face,i)=><div key={i} title={`Face ${i+1}: focus ${face.sharpness===null?"unavailable":Math.round(face.sharpness*100)+"%"}, ${face.blink<.5?"eyes open":"check eyes"}`}
              className="pointer-events-none absolute border border-cyan-300" style={{left:`${face.box[0]*100}%`,top:`${face.box[1]*100}%`,width:`${(face.box[2]-face.box[0])*100}%`,height:`${(face.box[3]-face.box[1])*100}%`}} />)}
          </div>
        </div>
        {!!p.quality?.face_regions?.length && <div className="mt-2 flex gap-2 overflow-x-auto">
          {p.quality.face_regions.map((face,i)=>{
            const [x0,y0,x1,y1]=face.box;const aspect=p.quality?.aspect_ratio??1;
            return <svg key={i} role="img" aria-label={`Face ${i+1} of ${p.name}`} width={72} height={72} className="shrink-0 rounded bg-black"
              viewBox={`${x0*aspect} ${y0} ${(x1-x0)*aspect} ${y1-y0}`}>
              <title>{`Face ${i+1}: focus ${face.sharpness===null?"unavailable":Math.round(face.sharpness*100)+"%"}`}</title>
              <image href={previewUrl(p.preview_path ?? p.rel_path)} width={aspect} height={1} preserveAspectRatio="none" />
            </svg>;
          })}
        </div>}
        <div className="mt-2"><FileDetails p={p}/></div>
        {onAssign && <Select aria-label={`Destination for ${p.name}`} className="mt-2 w-full" value={p.category_id} disabled={saving!==null}
          options={categories.map(c=>({value:c.id,label:c.name}))} onChange={async category=>{
            setSaving(p.file_id);try {await onAssign(p.file_id,category);} finally {setSaving(null);}
          }} />}
      </div>)}
    </div>
  </Modal>;
}

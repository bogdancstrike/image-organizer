import { expect, it, vi } from 'vitest';
const root=vi.hoisted(()=>({render:vi.fn()}));
vi.mock('react-dom/client',()=>({createRoot:vi.fn(()=>root)}));
it('mounts the application under its theme, language and strict-mode providers',async()=>{
 const element=document.createElement('div');element.id='root';document.body.append(element);
 await import('../src/main');
 const {createRoot}=await import('react-dom/client');expect(createRoot).toHaveBeenCalledWith(element);
 expect(root.render).toHaveBeenCalledOnce();expect(root.render.mock.calls[0][0].props.children).toBeDefined();element.remove();
});

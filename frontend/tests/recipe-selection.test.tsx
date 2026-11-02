import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import App from '../src/App';
import { api } from '../src/api';
import { DEFAULT_SETTINGS } from '../src/settings';
import { mockApi, renderUI } from './fixtures';

it('Quick settings Auto replaces the previously selected Boudoir recipe on Sort',async()=>{
 mockApi();vi.mocked(api.getSettings).mockResolvedValue({...DEFAULT_SETTINGS,source:'Trip',strategy:'preset',presetId:'boudoir',recipeId:'boudoir',recipeFor:'Trip'});
 renderUI(<App/>);
 await screen.findByRole('button',{name:/Boudoir \/ glamour/});
 fireEvent.click(screen.getByRole('button',{name:'Quick settings'}));
 fireEvent.click(await screen.findByText('Auto',{exact:true}));
 fireEvent.keyDown(document,{key:'Escape'});
 await waitFor(()=>expect(screen.getByRole('button',{name:/Not sure: discover/})).toHaveAttribute('aria-pressed','true'));
 expect(screen.getByRole('button',{name:/Boudoir \/ glamour/})).toHaveAttribute('aria-pressed','false');
 expect(screen.getByTitle('Change how files are organized')).toHaveTextContent('Auto-discover');
});

it('a late folder recommendation cannot overwrite an explicit Quick settings choice',async()=>{
 mockApi();let resolve!:(value:any)=>void;
 vi.mocked(api.getSettings).mockResolvedValue({...DEFAULT_SETTINGS,source:'Trip',recipeFor:null,presetId:'boudoir',recipeId:'boudoir'});
 vi.mocked(api.suggest).mockImplementation(()=>new Promise(r=>{resolve=r}));
 renderUI(<App/>);await waitFor(()=>expect(api.suggest).toHaveBeenCalled());
 fireEvent.click(screen.getByRole('button',{name:'Quick settings'}));fireEvent.click(await screen.findByText('Auto',{exact:true}));
 await waitFor(()=>expect(screen.getByTitle('Change how files are organized')).toHaveTextContent('Auto-discover'));
 await act(async()=>resolve({photos:4,videos:0,suggestions:[{recipe:'boudoir',reason:{key:'theme',theme:'Studio',pct:90}}]}));
 expect(screen.getByTitle('Change how files are organized')).toHaveTextContent('Auto-discover');
 expect(JSON.parse(localStorage.getItem('aio.settings.v1')!).strategy).toBe('auto');
});

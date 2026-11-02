import { fireEvent, screen, waitFor } from '@testing-library/react';
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

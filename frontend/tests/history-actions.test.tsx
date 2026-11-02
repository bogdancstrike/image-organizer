import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../src/api';
import { HistoryTab } from '../src/components/HistoryTab';
import { history, historyItem, mockApi, renderUI, run } from './fixtures';

beforeEach(()=>mockApi());

it('opens an applied run, empties trash and restores files from its details',async()=>{
 vi.mocked(api.history).mockResolvedValue({...history,counts:{...history.counts,applied:1},items:[{...historyItem,outcome:'applied',run:{...run,undo:{restored:0,problems:[]}}}]} as never);
 const undone=vi.fn();renderUI(<HistoryTab active onUndone={undone} onReopen={()=>{}}/>);
 fireEvent.click(await screen.findByRole('button',{name:/Trip.*AI prompt rules/}));
 fireEvent.click(await screen.findByRole('button',{name:/Empty trash/}));
 fireEvent.click(await screen.findByRole('button',{name:'OK',exact:true}));
 await waitFor(()=>expect(api.emptyTrash).toHaveBeenCalledWith('run-one'));
 fireEvent.click(await screen.findByRole('button',{name:/Trip.*AI prompt rules/}));
 fireEvent.click(screen.getByRole('button',{name:/Undo/}));fireEvent.click(await screen.findByRole('button',{name:'OK'}));
 await waitFor(()=>expect(undone).toHaveBeenCalledWith('run-one'));
});

it('reports undo failures without marking the history entry undone',async()=>{
 vi.mocked(api.history).mockResolvedValue({...history,items:[{...historyItem,outcome:'applied',run}]} as never);
 vi.mocked(api.undo).mockRejectedValue(Error('destination changed'));
 const undone=vi.fn();renderUI(<HistoryTab active onUndone={undone} onReopen={()=>{}}/>);
 fireEvent.click(await screen.findByRole('button',{name:/Trip.*AI prompt rules/}));
 fireEvent.click(await screen.findByRole('button',{name:/Undo/}));fireEvent.click(await screen.findByRole('button',{name:'OK'}));
 expect(await screen.findByText('destination changed')).toBeInTheDocument();expect(undone).not.toHaveBeenCalled();
});

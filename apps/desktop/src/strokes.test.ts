import { describe, expect, it } from 'vitest';
import { StrokeHistory, imagePoint } from './strokes';

describe('stroke journal', () => {
  it('discards redo branch after a new stroke and preserves undo', () => {
    const history = new StrokeHistory();
    history.add({ mode: 'paint', radius: 8, points: [[1, 2]] });
    history.add({ mode: 'erase', radius: 4, points: [[3, 4]] });
    history.undo();
    expect(history.strokes).toHaveLength(1);
    history.add({ mode: 'paint', radius: 6, points: [[5, 6]] });
    history.redo();
    expect(history.strokes.map(s => s.points[0])).toEqual([[1, 2], [5, 6]]);
    history.undo();
    history.redo();
    expect(history.strokes).toHaveLength(2);
  });
  it('maps zoomed and panned viewport coordinates to source pixels', () => {
    expect(imagePoint(110, 90, {left: 10, top: 30, width: 200, height: 100}, 1000, 500))
      .toEqual([500, 300]);
  });
  it('includes an active stroke in the rendered journal without committing it', () => {
    const history = new StrokeHistory();
    history.add({ mode: 'paint', radius: 8, points: [[1, 2]] });
    const active = { mode: 'erase' as const, radius: 4, points: [[3, 4] as [number, number]] };
    expect(history.visible(active)).toEqual([history.strokes[0], active]);
    expect(history.strokes).toHaveLength(1);
  });
});

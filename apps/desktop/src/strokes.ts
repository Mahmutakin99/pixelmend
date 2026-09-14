export type Stroke = { mode: 'paint' | 'erase'; radius: number; points: [number, number][] };

export class StrokeHistory {
  private readonly entries: Stroke[] = [];
  private cursor = 0;
  get strokes() { return this.entries.slice(0, this.cursor); }
  add(stroke: Stroke) { this.entries.splice(this.cursor); this.entries.push(stroke); this.cursor++; }
  undo() { if (this.cursor) this.cursor--; }
  redo() { if (this.cursor < this.entries.length) this.cursor++; }
  clear() { this.entries.splice(0); this.cursor = 0; }
}

export function imagePoint(clientX: number, clientY: number, rect: DOMRect | {left:number;top:number;width:number;height:number}, width: number, height: number): [number, number] {
  return [Math.max(0, Math.min(width, Math.round((clientX - rect.left) * width / rect.width))), Math.max(0, Math.min(height, Math.round((clientY - rect.top) * height / rect.height)))];
}

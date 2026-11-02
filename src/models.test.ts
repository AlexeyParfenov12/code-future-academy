import {describe,it,expect} from 'vitest';
import {topics,traces} from './learning';
import {slug} from './components/Content';
describe('teaching examples',()=>{
it('keeps the 15/20 example and its trace consistent',()=>{expect(15/20*100).toBe(75);const trace=traces.find(t=>t.id==='variables')!;expect(trace.steps.at(-1)?.output).toBe('75.0%');expect(trace.steps.at(-1)?.vars.percent).toBe('75.0')});
it('retains separate course references for 3.16 and 3.17',()=>{const topic=topics.find(t=>t.id==='overfitting')!;expect(topic.lessons).toContain('M03-L16');expect(topic.lessons).toContain('M03-L17')});
it('links every trace step to a real line',()=>{for(const trace of traces)for(const step of trace.steps){expect(step.line).toBeGreaterThan(0);expect(step.line).toBeLessThanOrEqual(trace.code.split('\n').length)}});
it('builds stable Cyrillic heading anchors',()=>{expect(slug('СЛАЙД 03. Условия в Python')).toBe('слайд-03-условия-в-python')});
});

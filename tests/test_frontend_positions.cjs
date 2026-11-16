// node --test tests/test_frontend_positions.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const html = fs.readFileSync(path.join(__dirname, '../app/templates/index.html'), 'utf8');
function between(start, end) {
    const from = html.indexOf(start), to = html.indexOf(end, from);
    assert.ok(from >= 0 && to > from);
    return html.slice(from, to);
}
class Element {
    constructor() { this.style = {}; this.listeners = {}; this.classList = {toggle() {}}; }
    addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
    fire(name, values = {}) {
        const event = {preventDefault() {}, stopPropagation() {}, ...values};
        for (const callback of this.listeners[name] || []) callback(event);
    }
    get offsetLeft() { return parseFloat(this.style.left) || 0; }
    get offsetTop() { return parseFloat(this.style.top) || 0; }
    get offsetWidth() { return parseFloat(this.style.width) || 200; }
    get offsetHeight() { return parseFloat(this.style.height) || 0; }
    querySelector(selector) { return selector === '.resize-handle' ? (this.handle ||= new Element()) : null; }
}
function setup(rotateLandscape, viewMode = 'all-grid', stampModel = 'padrao') {
    const elements = {};
    const document = new Element();
    document.getElementById = id => elements[id];
    const ctx = {
        document, MARGIN_RIGHT: 20, MARGIN_TOP: 20,
        STAMP_MODELS: {padrao: {width: 120.4, height: 60}, compacto: {width: 102.34, height: 44}, mini: {width: 102.34, height: 33}},
        undoStack: [], redoStack: [], scaleRange: {}, scaleValLabel: {}, posModeCheckbox: {},
        rotateLandscapeCheckbox: {}, btnUndo: {}, btnRedo: {},
    };
    vm.createContext(ctx);
    const initial = between('        let appState = ', '        // Pilhas de Histórico').replace('        let appState = ', '').trim().replace(/;$/, '');
    ctx.appState = vm.runInContext('(' + initial + ')', ctx);
    ctx.appState.rotateLandscape = rotateLandscape;
    ctx.appState.stampModel = stampModel;
    ctx.appState.viewMode = viewMode;
    ctx.appState.activeFileIdx = 0;
    ctx.appState.queue = ['first', 'second'].map(fileId => ({fileId, pages: [
        {page_idx: 0, width: 595, height: 842}, {page_idx: 1, width: 842, height: 595}
    ]}));
    vm.runInContext(between('        function initDragAndDrop(', '        function updateAllStampText(')
        + between('        function saveToHistory()', '        function sanitizeAndTruncateFilename('), ctx);
    ctx.appState.queue.forEach((file, fileIdx) => file.pages.forEach(page => {
        const stamp = elements[`stamp-page-${file.fileId}-${page.page_idx}`] = new Element();
        elements[`wrapper-page-${file.fileId}-${page.page_idx}`] = new Element();
        ctx.initDragAndDrop(stamp, fileIdx, page.page_idx, page.width, page.height);
    }));
    ctx.updateStampGeometries();
    const position = (file, page) => {
        const stamp = elements[`stamp-page-${file}-${page}`];
        return [stamp.offsetLeft, stamp.offsetTop];
    };
    const drag = (file, page, dx, dy) => {
        elements[`stamp-page-${file}-${page}`].fire('mousedown', {clientX: 100, clientY: 100});
        document.fire('mousemove', {clientX: 100 + dx, clientY: 100 + dy});
        document.fire('mouseup');
    };
    return {ctx, position, drag};
}
function close(actual, expected) {
    actual.forEach((value, idx) => assert.ok(Math.abs(value - expected[idx]) < 0.001, `${actual} != ${expected}`));
}

for (const rotate of [false, true]) {
    for (const model of ['padrao', 'compacto', 'mini']) {
        test(`dragging preserves opposite orientation, batch, undo/redo (${rotate}, ${model})`, () => {
            const {ctx, position, drag} = setup(rotate, 'all-grid', model);
            const portrait = position('first', 0), landscape = position('first', 1);
            drag('first', 0, -10, 10);
            close(position('first', 0), [portrait[0] - 10, portrait[1] + 10]);
            close(position('second', 0), position('first', 0));
            close(position('first', 1), landscape);
            close(position('second', 1), landscape);
            const movedPortrait = position('first', 0);
            drag('first', 1, -15, -3);
            close(position('first', 0), movedPortrait);
            close(position('second', 0), movedPortrait);
            const movedLandscape = position('first', 1);
            close(movedLandscape, [landscape[0] - 15, landscape[1] - 3]);
            close(position('second', 1), movedLandscape);
            ctx.undo();
            close(position('first', 0), movedPortrait);
            close(position('first', 1), landscape);
            ctx.undo();
            close(position('first', 0), portrait);
            close(position('first', 1), landscape);
            ctx.redo(); ctx.redo();
            close(position('first', 0), movedPortrait);
            close(position('first', 1), movedLandscape);
        });
    }
    test(`positions survive switching files in the single grid (${rotate})`, () => {
        const {ctx, position, drag} = setup(rotate, 'grid');
        const landscape = position('first', 1);
        drag('first', 0, -10, 10);
        const portrait = position('first', 0);
        ctx.appState.activeFileIdx = 1;
        ctx.updateStampGeometries();
        close(position('second', 0), portrait);
        close(position('second', 1), landscape);
        drag('second', 1, -15, -3);
        const movedLandscape = position('second', 1);
        ctx.appState.activeFileIdx = 0;
        ctx.updateStampGeometries();
        close(position('first', 0), portrait);
        close(position('first', 1), movedLandscape);
    });
}

test('custom positioning still affects only the selected page', () => {
    const {ctx, position, drag} = setup(true);
    ctx.appState.positionMode = true;
    const portrait = position('second', 0), landscape = position('first', 1);
    drag('first', 0, -10, 10);
    close(position('second', 0), portrait);
    close(position('first', 1), landscape);
    ctx.updateStampGeometries();
    close(position('second', 0), portrait);
});

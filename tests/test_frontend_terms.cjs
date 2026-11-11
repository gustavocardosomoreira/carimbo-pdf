// Executa as funções reais do template, sem dependências de navegador.
// node --test tests/test_frontend_terms.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const html = fs.readFileSync(path.join(__dirname, '../app/templates/index.html'), 'utf8');
function sourceBetween(start, end) {
    const from = html.indexOf(start);
    const to = html.indexOf(end, from);
    assert.ok(from >= 0 && to > from);
    return html.slice(from, to);
}
const sequenceSource = sourceBetween('        function recalculateSequences()', '        function updateActiveDocumentBadges()');
const gridSource = sourceBetween('        function getStampHTML(', '        function togglePageActive(');

// DOM mínimo para inspecionar os nós produzidos pelo renderizador real.
class Element {
    constructor(tag = 'div') {
        this.tag = tag;
        this.children = [];
        this.attributes = {};
        this.style = {setProperty() {}};
        this.className = '';
        this.classList = {add: value => { this.className += ' ' + value; }};
    }
    set innerHTML(value) { this.markup = value; this.children = []; }
    appendChild(child) { this.children.push(child); return child; }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    addEventListener() {}
}
function descendants(element) {
    return element.children.flatMap(child => [child, ...descendants(child)]);
}
function file(id, count, activePages = Array.from({length: count}, (_, i) => i)) {
    return {
        fileId: id, filename: id + '.pdf', totalPages: count, activePages,
        pages: Array.from({length: count}, (_, page_idx) => ({page_idx, width: 595, height: 842}))
    };
}
function setup(queue, viewMode = 'single', startLeaf = 198) {
    const ctx = {
        appState: {queue, activeFileIdx: 0, viewMode, startLeaf, volumeLimit: 200,
            reserveTerms: true, stampModel: 'padrao', processNumber: '123/2026', startDate: '11/11/2026'},
        document: {createElement: tag => new Element(tag), documentElement: new Element(), getElementById: () => new Element()},
        pagesGrid: new Element(), emptyState: new Element(), documentTitle: new Element(),
        zoomRange: {value: '200'}, volumeAlertText: {}, volumeAlertContainer: new Element(),
        IntersectionObserver: class { observe() {} },
        updateActiveDocumentBadges() {}, updateBgGeometries() {}, updateStampGeometries() {},
        updateAllStampText() {}, initDragAndDrop() {},
        formatProcessNumberJS: value => value, formatStartDateJS: value => value,
    };
    vm.createContext(ctx);
    vm.runInContext(sequenceSource + gridSource, ctx);
    ctx.recalculateSequences();
    return ctx;
}
const plain = value => JSON.parse(JSON.stringify(value));
function cards(ctx) {
    return descendants(ctx.pagesGrid).filter(el => el.className.split(' ').includes('page-container'));
}

for (const mode of ['single', 'all-grid']) {
    test(`six PDF pages plus two independent term cards (${mode})`, () => {
        const ctx = setup([file('six', 6)], mode);
        assert.deepEqual(plain(ctx.appState.queue[0].pagesInfo.map(p => p.leaf_number)), [198, 199, 202, 203, 204, 205]);
        ctx.renderGrid();
        assert.deepEqual(cards(ctx).map(c => c.id), [
            'page-container-six-0', 'page-container-six-1',
            'term-placeholder-six-200', 'term-placeholder-six-201',
            'page-container-six-2', 'page-container-six-3', 'page-container-six-4', 'page-container-six-5'
        ]);
        const nodes = descendants(ctx.pagesGrid);
        assert.equal(nodes.filter(el => el.className === 'page-img').length, 6);
        assert.equal(nodes.filter(el => el.className === 'stamp-overlay').length, 6);
        const terms = cards(ctx).filter(el => el.id.startsWith('term-placeholder-'));
        assert.ok(descendants(terms[0]).some(el => el.textContent === 'Termo de Encerramento'));
        assert.ok(descendants(terms[1]).some(el => el.textContent === 'Termo de Abertura'));
        assert.equal(terms.flatMap(descendants).filter(el => el.tag === 'button' || el.tag === 'img').length, 0);
    });

    test(`switching reservation off and on rebuilds cards (${mode})`, () => {
        const ctx = setup([file('six', 6)], mode);
        for (const reserve of [true, false, true]) {
            ctx.appState.reserveTerms = reserve;
            ctx.recalculateSequences();
            ctx.renderGrid();
            assert.equal(cards(ctx).length, reserve ? 8 : 6);
            assert.deepEqual(plain(ctx.appState.queue[0].pagesInfo.map(p => p.leaf_number)),
                reserve ? [198, 199, 202, 203, 204, 205] : [198, 199, 200, 201, 202, 203]);
        }
    });
}

test('batch continuity reserves terms in the next file, preserving real indices', () => {
    const ctx = setup([file('first', 2), file('second', 4)], 'all-grid');
    assert.equal(ctx.appState.queue[1].startLeafCalculated, 200);
    assert.deepEqual(plain(ctx.appState.queue[1].pagesInfo.map(p => p.leaf_number)), [202, 203, 204, 205]);
    ctx.renderGrid();
    assert.deepEqual(cards(ctx).map(c => c.id), [
        'page-container-first-0', 'page-container-first-1',
        'term-placeholder-second-200', 'term-placeholder-second-201',
        'page-container-second-0', 'page-container-second-1', 'page-container-second-2', 'page-container-second-3'
    ]);
});

test('inactive pages neither consume numbers nor receive term cards', () => {
    const ctx = setup([file('mixed', 6, [0, 2, 3, 5])]);
    assert.deepEqual(plain(ctx.appState.queue[0].pagesInfo.map(p => p.leaf_number)), [198, null, 199, 202, null, 203]);
    assert.deepEqual(plain(ctx.appState.queue[0].termsBeforePage), {'3': [200, 201]});
    ctx.renderGrid();
    assert.equal(cards(ctx).length, 8);
});

test('no numbering and the first leaf do not reserve opening terms', () => {
    for (const startLeaf of [null, 1]) {
        const ctx = setup([file('first', 3)], 'single', startLeaf);
        ctx.renderGrid();
        assert.equal(cards(ctx).length, 3);
        assert.deepEqual(plain(ctx.appState.queue[0].termsBeforePage), {});
    }
});

test('multiple volume boundaries reserve each pair exactly once', () => {
    const ctx = setup([file('many', 12)], 'all-grid', 8);
    ctx.appState.volumeLimit = 10;
    ctx.recalculateSequences();
    ctx.renderGrid();
    assert.deepEqual(cards(ctx).filter(c => c.id.startsWith('term-placeholder-')).map(c => c.id), [
        'term-placeholder-many-10', 'term-placeholder-many-11',
        'term-placeholder-many-20', 'term-placeholder-many-21'
    ]);
});

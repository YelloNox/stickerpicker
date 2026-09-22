import {readFileSync} from 'node:fs'
import assert from 'node:assert/strict'
import {test} from 'node:test'
const code = readFileSync(new URL('../web/src/search.js', import.meta.url), 'utf8')
const {stickerMatches} = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)
const pack = {title: 'Leo Faves'}
const sticker = {body: '🙂', tags: ['comfort'], excluded_tags: ['wrong_tag'],
	auto_tags: {tags: [{tag: 'hugging', score: .9}, {tag: 'closed_eyes', score: .8}, {tag: 'wrong_tag', score: .5}]},
	'net.maunium.telegram.sticker': {emoticons: ['🤗']}}
test('generated and manual tags, multi-term searches, pack names and emoji', () => {
	for (const query of ['hug', 'HUGGING closed_eyes', 'closed eyes', 'comfort', 'leo hugging', '🤗', '']) {
		assert.equal(stickerMatches(sticker, pack, query), true, query)
	}
	assert.equal(stickerMatches(sticker, pack, 'wrong tag'), false)
	assert.equal(stickerMatches(sticker, pack, 'hugging angry'), false)
})
test('legacy and incomplete stickers remain searchable', () => {
	assert.equal(stickerMatches({body: 'Hello'}, pack, 'hello'), true)
	assert.equal(stickerMatches({}, {}, 'hello'), false)
	assert.equal(stickerMatches({id: 123}, {}, '123'), true)
})

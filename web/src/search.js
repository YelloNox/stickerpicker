// Search generated tags alongside user-curated tags and existing sticker metadata.
const normalize = value => String(value ?? "").toLowerCase().replaceAll("_", " ").trim()

export function stickerMatches(sticker, pack, query) {
	const terms = normalize(query).split(/\s+/).filter(Boolean)
	const excluded = new Set((sticker.excluded_tags ?? []).map(normalize))
	const generated = (sticker.auto_tags?.tags ?? []).map(item => item.tag)
	const tags = [...(sticker.tags ?? []), ...generated].filter(tag => !excluded.has(normalize(tag)))
	const telegram = sticker["net.maunium.telegram.sticker"]
	const fields = [sticker.body, sticker.id, pack.title,
		pack["net.maunium.telegram.pack"]?.short_name,
		telegram?.pack?.short_name, ...(telegram?.emoticons ?? []), ...tags].map(normalize)
	return terms.every(term => fields.some(field => field.includes(term)))
}

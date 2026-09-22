// Bound both the request and response parsing so stalled loads report an error.
export async function fetchJSON(url, cache, timeoutMs = 30000) {
	const controller = new AbortController()
	let timer
	try {
		return await Promise.race([
			(async () => {
				const response = await fetch(url, {cache, signal: controller.signal})
				if (!response.ok) {
					throw new Error(`HTTP ${response.status}`)
				}
				return await response.json()
			})(),
			new Promise((_, reject) => {
				timer = setTimeout(() => {
					reject(new Error("Request timed out"))
					controller.abort()
				}, timeoutMs)
			}),
		])
	} catch (error) {
		throw new Error(`Could not load ${url}: ${error.message || error}`)
	} finally {
		clearTimeout(timer)
	}
}

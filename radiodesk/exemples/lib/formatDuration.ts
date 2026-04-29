function formatClockTime(totalSeconds: number): string {
	const safeSeconds = Math.max(0, Math.round(totalSeconds));
	const hours = Math.floor(safeSeconds / 3600);
	const minutes = Math.floor((safeSeconds % 3600) / 60);
	const seconds = safeSeconds % 60;

	if (hours > 0) {
		return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
	}

	return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function parseIsoDuration(value: string): number | null {
	const trimmed = value.trim();
	const match = trimmed.match(/^PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$/i);
	if (!match) return null;

	const hours = match[1] ? Number(match[1]) : 0;
	const minutes = match[2] ? Number(match[2]) : 0;
	const seconds = match[3] ? Number(match[3]) : 0;
	const totalSeconds = hours * 3600 + minutes * 60 + seconds;
	return Number.isFinite(totalSeconds) ? totalSeconds : null;
}

export function formatDuration(value: unknown): string {
	if (value === null || typeof value === 'undefined') return '';

	const text = String(value).trim();
	if (!text) return '';

	if (/^\d+(?:\.\d+)?$/.test(text)) {
		return formatClockTime(Number(text));
	}

	const isoSeconds = parseIsoDuration(text);
	if (isoSeconds !== null) {
		return formatClockTime(isoSeconds);
	}

	if (/^(?:\d+:)?\d{1,2}:\d{2}$/.test(text)) {
		return text;
	}

	return text;
}
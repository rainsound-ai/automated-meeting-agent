<script lang="ts">
	import * as Urls from '../lib/Urls.shared';
	import type { TranscriptionRequest, TranscriptionResponse } from '../lib/ApiTypes';
	import '../app.css';

	// Declare variable types
	let file: File | null = null;
	let fileName: string = '';
	let transcription: string = '';
	let summary: string = '';
	let isLoadingTranscription: boolean = false;
	let isLoadingSummary: boolean = false;
	let error: string = '';
	let copiedTranscription: boolean = false;
	let copiedSummary: boolean = false;
	let loadingMessage: string = ''; // To hold the current loading message
	let intervalId: number; // For the setInterval reference
	let phraseIndex: number = 0; // To cycle through phrases
	let ellipsisCount: number = 0; // To control how many ellipses are shown

	const loadingPhrases: string[] = ['Whirring away', 'Thinking hard', 'Processing'];

	// Function to handle the ellipsis logic
	const startLoadingAnimation = () => {
		phraseIndex = 0;
		ellipsisCount = 0;
		loadingMessage = loadingPhrases[phraseIndex];

		intervalId = setInterval(() => {
			ellipsisCount = (ellipsisCount + 1) % 6; // Add up to 5 ellipses
			if (ellipsisCount === 0) {
				// Switch to the next phrase after 5 ellipses
				phraseIndex = (phraseIndex + 1) % loadingPhrases.length;
				loadingMessage = loadingPhrases[phraseIndex];
			}
			loadingMessage = `${loadingPhrases[phraseIndex]}${'.'.repeat(ellipsisCount)}`;
			updateUI(); // Update the UI to reflect the new loading message
		}, 1000);
	};

	// Stop the loading animation when loading is complete
	const stopLoadingAnimation = () => {
		clearInterval(intervalId); // Stop the interval
		loadingMessage = ''; // Clear the loading message
		updateUI(); // Update the UI
	};

	const handleFileChange = (event: Event) => {
		const target = event.target as HTMLInputElement;
		file = target.files ? target.files[0] : null;
		fileName = file ? file.name : '';
		error = '';
		transcription = '';
		summary = '';
		updateUI();
	};

	const transcribeAudio = async () => {
		if (!file) {
			alert('Please select an audio or video file first.');
			return;
		}

		isLoadingTranscription = true;
		transcription = '';
		summary = '';
		error = '';
		startLoadingAnimation(); // Start the animation
		updateUI();

		const formData = new FormData();
		formData.append('file', file);

		try {
			const response = await fetch(`${Urls.apiRoot()}/transcribe`, {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'An error occurred during transcription.');
			}

			const data: TranscriptionResponse = await response.json();
			transcription = data.transcription;
		} catch (err) {
			error = (err as Error).message;
		} finally {
			isLoadingTranscription = false;
			stopLoadingAnimation(); // Stop the animation
			updateUI();
		}
	};

	const summarizeTranscription = async () => {
		if (!transcription) {
			try {
				// Fetch the first line of transcription.txt (file name)
				const response = await fetch(`${Urls.apiRoot()}/get_transcription_file_name`, {
					method: 'GET'
				});

				if (!response.ok) {
					throw new Error('Unable to retrieve transcription file name.');
				}

				const data = await response.json();

				if (data.file_not_found) {
					// Display a message if the file was not found
					alert(
						`Couldn't find a transcription to summarize. Please generate one by uploading a file and clicking Transcribe.`
					);
					return; // Prevent further execution if no file is found
				}

				const fileName = data.file_name; // Get the file name from the response

				// Ask the user for confirmation, including the file name
				const userConfirmed = confirm(
					`I couldn't find a transcription in memory. Do you want to summarize the contents of ${fileName}? That was the last transcription you ran as far as I know.`
				);
				if (!userConfirmed) {
					return; // User declined, so do not proceed
				}
			} catch (err) {
				console.log(err);
				alert(
					`Couldn't find a transcription to summarize. Please generate one by uploading a file and clicking Transcribe.`
				);
				return; // Prevent further execution if error occurs
			}
		}

		// Continue with summarization if transcription is available
		isLoadingSummary = true;
		error = '';
		startLoadingAnimation(); // Start the animation
		updateUI();

		try {
			const transcriptionRequest: TranscriptionRequest = {
				transcription: transcription
			};

			const response = await fetch(`${Urls.apiRoot()}/summarize`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(transcriptionRequest)
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'An error occurred during summarization.');
			}

			const data = await response.json();
			summary = data.summary;
		} catch (err) {
			error = (err as Error).message;
		} finally {
			isLoadingSummary = false;
			stopLoadingAnimation(); // Stop the animation
			updateUI();
		}
	};

	const updateUI = () => {
		document.getElementById('transcription-content')!.innerText = isLoadingTranscription
			? loadingMessage || 'Loading...'
			: transcription || 'Transcription will appear here.';
		document.getElementById('summary-content')!.innerText = isLoadingSummary
			? loadingMessage || 'Loading...'
			: summary || 'Summary will appear here.';
		document.getElementById('transcribe-btn')!.innerText = isLoadingTranscription
			? 'Transcribing...'
			: 'Transcribe';
		document.getElementById('summarize-btn')!.innerText = isLoadingSummary
			? 'Summarizing...'
			: 'Summarize';
		if (error) {
			document.getElementById('error-message')!.innerText = error;
		}
	};

	const copyText = (containerId: string, type: string) => {
		const text = document.getElementById(containerId)!.innerText;
		navigator.clipboard.writeText(text).then(() => {
			if (type === 'transcription') {
				copiedTranscription = true;
			} else {
				copiedSummary = true;
			}
			setTimeout(() => {
				if (type === 'transcription') {
					copiedTranscription = false;
				} else {
					copiedSummary = false;
				}
			}, 2000);
		});
	};
</script>

<div class="min-h-screen bg-[#faf7f4] flex flex-col items-center justify-center p-10">
	<!-- Header with buttons -->
	<div class="w-full max-w-6xl flex justify-between items-center mb-6">
		<!-- Transcribe Button (Top-Left) -->
		<button
			id="transcribe-btn"
			class="bg-gray-800 text-white py-3 px-6 rounded-md hover:bg-gray-900 focus:ring-4 focus:ring-gray-300 transition"
			on:click={transcribeAudio}
			disabled={!file || isLoadingTranscription}
		>
			Transcribe
		</button>

		<!-- Meeting Summarization Title -->
		<h1 class="text-3xl font-light text-gray-800 text-center">Meeting Agent</h1>

		<!-- Summarize Button (Top-Right) -->
		<button
			id="summarize-btn"
			class="bg-gray-800 text-white py-3 px-6 rounded-md hover:bg-gray-900 focus:ring-4 focus:ring-gray-300 transition"
			on:click={summarizeTranscription}
		>
			Summarize
		</button>
	</div>
	<!-- File input -->
	<!-- File input wrapped in the same container as text areas -->
	<div class="w-full max-w-6xl">
		<div class="flex justify-center w-full">
			<label
				class="flex flex-col items-center w-full py-8 bg-[#f2ede7] rounded-lg border border-gray-300 cursor-pointer hover:border-gray-400"
			>
				<input
					type="file"
					accept="audio/*,.mp3,.wav,.m4a,video/*,.mp4,.mov,.avi"
					class="hidden"
					on:change={handleFileChange}
				/>
				<span class="text-gray-600 text-lg">
					{fileName ? `Selected: ${fileName}` : 'Click to select an audio or video file'}
				</span>
			</label>
		</div>
	</div>

	<!-- Side-by-side panes for transcription and summary -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6 w-full max-w-6xl">
		<!-- Transcription Pane -->
		<div class="relative flex flex-col">
			<h2 class="text-xl font-semibold text-gray-700 mb-2">Transcription</h2>
			<!-- Copy Button Inside Text Area -->
			<div class="relative overflow-y-auto h-64 p-4 bg-[#f6f3f0] border border-gray-200 rounded-lg">
				<!-- <button
					class="absolute right-2 top-2 bg-[#e2dfdb] px-2 py-1 rounded-md hover:bg-gray-300 transition"
					on:click={() => copyText('transcription-content', 'transcription')}
				>
					{copiedTranscription ? 'Copied' : 'Copy'}
				</button> -->
				<div id="transcription-content" class="pt-6">Transcription will appear here.</div>
			</div>
		</div>

		<!-- Summary Pane -->
		<div class="relative flex flex-col">
			<h2 class="text-xl font-semibold text-gray-700 mb-2">Summary</h2>
			<!-- Copy Button Inside Text Area -->
			<div class="relative overflow-y-auto h-64 p-4 bg-[#f6f3f0] border border-gray-200 rounded-lg">
				<button
					class="absolute right-2 top-2 bg-[#e2dfdb] px-2 py-1 rounded-md hover:bg-gray-300 transition"
					on:click={() => copyText('summary-content', 'summary')}
				>
					{copiedSummary ? 'Copied' : 'Copy'}
				</button>
				<div id="summary-content" class="pt-6">Summary will appear here.</div>
			</div>
		</div>
	</div>

	<!-- Error Message -->
	<div id="error-message" class="text-red-500 mt-4 text-center"></div>
</div>

<style>
	:root {
		--transition-speed: 300ms;
	}

	button,
	div {
		transition:
			background-color var(--transition-speed),
			box-shadow var(--transition-speed);
	}
</style>

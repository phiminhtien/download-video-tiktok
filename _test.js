
        let currentImages = [];
        let currentIdx = 0;

        function getExt(f) { return f.split('.').pop().toLowerCase(); }
        function isImg(f) { return ['jpg','jpeg','png','webp'].includes(getExt(f)); }
        function isVid(f) { return ['mp4','webm','mkv','mov'].includes(getExt(f)); }
        function isAud(f) { return !isImg(f) && !isVid(f); }

        function showStatus(msg, type) {
            const el = document.getElementById('status');
            el.className = 'status show';
            if (type === 'loading') {
                el.innerHTML = `<div class="status-box"><div class="spinner"></div><div class="status-text">${msg}</div></div>`;
            } else if (type === 'error') {
                el.innerHTML = `<div class="status-box error"><div class="error-msg">${msg}</div><div class="error-hint">Thử cập nhật: py -m pip install -U yt-dlp</div></div>`;
            }
        }

        function hideStatus() {
            document.getElementById('status').className = 'status';
        }

        function formatSize(mb) { return mb >= 1 ? mb + ' MB' : (mb * 1024).toFixed(0) + ' KB'; }

        function openLightbox(src, idx) {
            currentIdx = idx;
            const lb = document.getElementById('lightbox');
            document.getElementById('lightboxImg').src = src;
            document.getElementById('lightboxCounter').textContent = `${idx + 1} / ${currentImages.length}`;
            lb.className = 'lightbox show';
        }

        function closeLightbox(e) {
            if (e.target.tagName !== 'IMG') document.getElementById('lightbox').className = 'lightbox';
        }

        function navLightbox(dir, e) {
            e.stopPropagation();
            currentIdx = (currentIdx + dir + currentImages.length) % currentImages.length;
            document.getElementById('lightboxImg').src = currentImages[currentIdx];
            document.getElementById('lightboxCounter').textContent = `${currentIdx + 1} / ${currentImages.length}`;
        }

        document.addEventListener('keydown', e => {
            if (!document.getElementById('lightbox').classList.contains('show')) return;
            if (e.key === 'Escape') document.getElementById('lightbox').className = 'lightbox';
            if (e.key === 'ArrowLeft') navLightbox(-1, e);
            if (e.key === 'ArrowRight') navLightbox(1, e);
        });

        async function startDownload() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url || !url.includes('tiktok')) {
                showStatus('Vui lòng nhập link TikTok hợp lệ', 'error');
                return;
            }

            const btn = document.getElementById('downloadBtn');
            btn.disabled = true;
            document.getElementById('result').className = 'result';
            showStatus('Đang tải...', 'loading');

            try {
                const resp = await fetch('/api/download', {
                    method: 'POST',
                    body: new URLSearchParams({ url })
                });
                const data = await resp.json();

                if (!data.success) {
                    showStatus(data.error || 'Tải thất bại', 'error');
                    return;
                }

                hideStatus();

                const images = data.files.filter(isImg);
                const videos = data.files.filter(isVid);
                const audios = data.files.filter(isAud);
                const isVideo = data.type === 'video' || videos.length > 0;

                // Badge
                const badge = document.getElementById('resultBadge');
                if (isVideo) {
                    badge.className = 'result-badge badge-video';
                    badge.innerHTML = '🎬 Video';
                } else {
                    badge.className = 'result-badge badge-images';
                    badge.innerHTML = '🖼 Ảnh slideshow';
                }

                document.getElementById('resultSize').textContent = formatSize(data.size_mb);

                const folder = data.folder || '';
                const folderInfo = document.getElementById('folderInfo');
                if (folder) {
                    folderInfo.textContent = `📁 downloads/${folder}/`;
                    folderInfo.style.display = 'block';
                } else {
                    folderInfo.style.display = 'none';
                }

                // Preview
                const preview = document.getElementById('previewArea');
                preview.innerHTML = '';
                currentImages = [];

                if (isVideo) {
                    const v = document.createElement('video');
                    v.controls = true; v.playsInline = true; v.preload = 'metadata';
                    v.src = `/downloads/${videos[0] || data.files[0]}`;
                    preview.appendChild(v);
                } else if (images.length > 0) {
                    const gallery = document.createElement('div');
                    gallery.className = 'image-gallery';
                    images.forEach((f, i) => {
                        const img = document.createElement('img');
                        img.src = `/downloads/${f}`;
                        img.alt = `Ảnh ${i+1}`;
                        img.loading = 'lazy';
                        const fullSrc = `/downloads/${f}`;
                        currentImages.push(fullSrc);
                        img.onclick = () => openLightbox(fullSrc, i);
                        gallery.appendChild(img);
                    });
                    preview.appendChild(gallery);
                }

                    // File list
                    const fileEl = document.getElementById('fileList');
                    fileEl.innerHTML = '';
                    data.files.forEach(f => {
                        const fname = f.includes('/') ? f.split('/').pop() : f;
                        const ext = getExt(fname);
                        let icon = '📄', cls = 'img';
                        if (isVid(f)) { icon = '🎬'; cls = 'vid'; }
                        else if (isAud(f)) { icon = '🎵'; cls = 'aud'; }
                        else if (isImg(f)) { icon = '🖼'; cls = 'img'; }

                        fileEl.innerHTML += `
                            <div class="file-row">
                                <div class="file-info">
                                    <div class="file-icon ${cls}">${icon}</div>
                                    <div class="file-name">${fname}</div>
                                </div>
                                <a href="/downloads/${f}" download class="btn-action ${cls === 'aud' ? 'purple' : 'green'}" style="flex:0;padding:8px 16px;font-size:12px;">Tải</a>
                            </div>`;
                    });

                // Action buttons
                const actions = document.getElementById('resultActions');
                actions.innerHTML = '';
                if (isVideo) {
                    actions.innerHTML = `<a class="btn-action gradient" href="/downloads/${videos[0] || data.files[0]}" download>⬇ Tải video</a>`;
                } else {
                    if (images.length > 1) {
                        actions.innerHTML += `<a class="btn-action green" href="/downloads/${images[0]}" download>⬇ Ảnh đầu</a>`;
                    }
                    if (audios.length > 0) {
                        actions.innerHTML += `<a class="btn-action purple" href="/downloads/${audios[0]}" download>🎵 Tải nhạc</a>`;
                    }
                }

                document.getElementById('result').className = 'result show';

            } catch (e) {
                showStatus('Lỗi kết nối đến server', 'error');
            } finally {
                btn.disabled = false;
            }
        }

        document.getElementById('urlInput').addEventListener('keydown', e => {
            if (e.key === 'Enter') startDownload();
        });
    
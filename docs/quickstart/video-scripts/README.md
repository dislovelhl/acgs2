# ACGS-2 Video Production Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

This directory contains scripts and production guidelines for ACGS-2 tutorial videos.

## Video Inventory

| Video | Script | Status | Duration | Target Audience |
|-------|--------|--------|----------|-----------------|
| [Quickstart Walkthrough](./01-quickstart-walkthrough.md) | Complete | Pending Recording | 8-10 min | New developers |
| [Example Project Walkthrough](./02-example-project-walkthrough.md) | Complete | Pending Recording | 10-12 min | Intermediate developers |
| [Jupyter Notebook Tutorial](./03-jupyter-notebook-tutorial.md) | Complete | Pending Recording | 8-10 min | Data scientists |

## Production Standards

### Technical Requirements

| Specification | Requirement |
|---------------|-------------|
| **Resolution** | 1920x1080 (1080p) minimum |
| **Frame Rate** | 30fps |
| **Audio** | Clear mono/stereo, -12dB to -6dB levels |
| **Format** | MP4 (H.264 video, AAC audio) |
| **Bitrate** | 8-12 Mbps for 1080p |

### Recording Setup

1. **Screen Recording Software**
   - OBS Studio (free, cross-platform)
   - Camtasia (paid, easier editing)
   - macOS: QuickTime Player (built-in)

2. **Terminal Configuration**
   - Font size: 14pt minimum (16pt recommended)
   - High contrast theme (dark terminal, light text)
   - Clear prompt showing current directory
   - Terminal width: 120+ characters

3. **Audio Setup**
   - USB microphone or headset
   - Quiet recording environment
   - Record test clip first to check levels

### Visual Guidelines

1. **Terminal Commands**
   - Show full command before pressing Enter
   - Pause 1-2 seconds after output
   - Use colored output when available

2. **Annotations**
   - Add callouts for important output
   - Highlight version numbers, URLs, success messages
   - Use consistent annotation style

3. **Transitions**
   - Simple fade transitions between sections
   - No flashy effects
   - Chapter markers at major sections

### Content Guidelines

1. **Pacing**
   - Speak clearly and at moderate pace
   - Allow time for viewers to read output
   - Don't rush through commands

2. **Error Handling**
   - If you make a mistake, it's okay to show the fix
   - Real-world developers encounter errors too
   - Explain what went wrong and how to fix it

3. **Consistency**
   - Use the same terminal and browser throughout
   - Use the same Docker Compose file as documentation
   - Match all commands exactly to written docs

## Recording Workflow

### Pre-Recording Checklist

- [ ] Script reviewed and tested
- [ ] Clean Docker environment (no leftover containers)
- [ ] Internet connection stable
- [ ] Recording software tested
- [ ] Audio levels checked
- [ ] Notifications disabled
- [ ] Clean desktop/browser

### Recording Steps

1. **Setup**
   ```bash
   # Clean Docker environment
   docker compose down -v
   docker system prune -f

   # Prepare terminal
   cd /tmp  # Or fresh directory
   clear
   ```

2. **Recording**
   - Start recording software
   - Begin with intro slide (5 seconds)
   - Follow script exactly
   - Pause between sections
   - End with outro slide

3. **Post-Recording**
   - Review recording for issues
   - Note timestamps for chapters
   - Export for editing

### Post-Production Checklist

- [ ] Add intro/outro branding
- [ ] Add chapter markers
- [ ] Add captions/subtitles
- [ ] Add on-screen annotations
- [ ] Review audio levels
- [ ] Export in 1080p
- [ ] Get team review

## Publishing Workflow

### Video Hosting Options

1. **YouTube (Primary)**
   - Create ACGS-2 channel or use organization channel
   - Playlist: "ACGS-2 Tutorials"
   - Enable captions/subtitles
   - Add timestamps in description

2. **Vimeo (Alternative)**
   - Better for embedded viewing
   - No ads
   - More professional appearance

### After Publishing

1. **Update Documentation**
   - Replace VIDEO_PLACEHOLDER comments with actual embeds
   - Update video production status table
   - Add video links to README files

2. **Video Description Template**
   ```
   ACGS-2 Tutorial: [Video Title]

   This video shows you how to [brief description].

   Timestamps:
   0:00 - Introduction
   [... add all chapter markers ...]

   Resources:
   - Written Guide: [link to docs]
   - GitHub Repository: https://github.com/ACGS-Project/ACGS-2
   - Feedback Form: [link to feedback]

   Constitutional Hash: cdd01ef066bc6cf2
   ```

## Maintaining Videos

### Update Triggers

Videos should be re-recorded when:
- Major version changes to ACGS-2
- Command syntax changes
- UI/output significantly changes
- New features are added to the covered workflow

### Version Tracking

Track video versions in this file:

| Video | Version | ACGS-2 Version | Date | Notes |
|-------|---------|----------------|------|-------|
| Quickstart Walkthrough | 1.0.0 | 2.x | TBD | Initial recording |
| Example Project Walkthrough | 1.0.0 | 2.x | TBD | Initial recording |
| Jupyter Notebook Tutorial | 1.0.0 | 2.x | TBD | Initial recording |

## Contributing

Want to help with video production?

1. **Recording**: Check script, record following guidelines
2. **Editing**: Add annotations, chapters, polish
3. **Review**: Watch videos for accuracy, timing, clarity
4. **Translations**: Add subtitles in other languages

Contact the documentation team or open an issue tagged `documentation` and `video`.

---

*Last Updated: 2026-01-03*
*Constitutional Hash: cdd01ef066bc6cf2*

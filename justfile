set quiet

# Reset sample directory, clear logs and reprocess it
optimize-test-videos-clean:
    rm -fr videos
    cp -r videos.bak videos
    rm -f NanoEncoder.log NanoEncoder_ffmpeg.log
    nen optimize videos

# Test partial video handling with sample directory
optimize-test-videos:
    rm -f NanoEncoder.log NanoEncoder_ffmpeg.log
    nen optimize videos

# Reset sample directory
reset-test-videos:
    rm -fr videos
    cp -r videos.bak videos

# Remove all test items
clean-test-env:
    rm -rf NanoEncoder.log NanoEncoder_ffmpeg.log videos

# Full "test"
full-test:
    rm -fr videos
    cp -r videos.bak videos
    nen optimize --preset fast --crf 26 --tune animation videos
    nen health --full videos
    nen purge --force
    nen untag videos

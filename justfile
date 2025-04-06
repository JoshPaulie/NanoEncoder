# Reset sample directory, clear logs and reprocess it
encode-test-videos-clean:
    rm -fr videos
    cp -r videos.bak videos
    rm -f NanoEncoder.log NanoEncoder_ffmpeg.log
    nen encode videos

# Test partial video handling with sample directory
encode-test-videos:
    rm -f NanoEncoder.log NanoEncoder_ffmpeg.log
    nen encode videos

# Reset sample directory
reset-test-videos:
    rm -fr videos
    cp -r videos.bak videos

# Remove all test items
clean-test-env:
    rm -rf NanoEncoder.log NanoEncoder_ffmpeg.log videos

import Foundation
import AVFoundation
import CoreMedia
import CoreVideo

final class SharedState {
    let lock = NSLock()
    var latestFrame: Data?
    var width: Int = 0
    var height: Int = 0
    var stride: Int = 0
    var session: AVCaptureSession?
    var output: AVCaptureVideoDataOutput?
    var input: AVCaptureDeviceInput?
    var delegate: FrameDelegate?
    var queue: DispatchQueue?
}

final class FrameDelegate: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let state: SharedState

    init(state: SharedState) {
        self.state = state
        super.init()
    }

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }

        let width = CVPixelBufferGetWidthOfPlane(pixelBuffer, 0)
        let height = CVPixelBufferGetHeightOfPlane(pixelBuffer, 0)
        let stride = CVPixelBufferGetBytesPerRowOfPlane(pixelBuffer, 0)

        guard let base = CVPixelBufferGetBaseAddressOfPlane(pixelBuffer, 0) else { return }

        let size = stride * height
        let frameData = Data(bytes: base, count: size)

        state.lock.lock()
        state.latestFrame = frameData
        state.width = width
        state.height = height
        state.stride = stride
        state.lock.unlock()
    }
}

let gState = SharedState()

func fourCCString(_ code: FourCharCode) -> String {
    let chars: [UInt8] = [
        UInt8((code >> 24) & 0xff),
        UInt8((code >> 16) & 0xff),
        UInt8((code >> 8) & 0xff),
        UInt8(code & 0xff),
    ]
    return String(bytes: chars, encoding: .ascii) ?? "\(code)"
}

func chooseDevice() -> AVCaptureDevice? {
    let discovery = AVCaptureDevice.DiscoverySession(
        deviceTypes: [.externalUnknown, .builtInWideAngleCamera],
        mediaType: .video,
        position: .unspecified
    )

    return discovery.devices.first { $0.localizedName.lowercased().contains("arducam") }
        ?? discovery.devices.first
}

func chooseFormat(
    device: AVCaptureDevice,
    targetWidth: Int32,
    targetHeight: Int32,
    targetFPS: Double
) -> (AVCaptureDevice.Format, AVFrameRateRange)? {
    let eps = 0.5

    for format in device.formats {
        let desc = format.formatDescription
        let dims = CMVideoFormatDescriptionGetDimensions(desc)
        let codec = fourCCString(CMFormatDescriptionGetMediaSubType(desc))

        guard dims.width == targetWidth, dims.height == targetHeight else { continue }
        guard codec == "420v" else { continue }

        for range in format.videoSupportedFrameRateRanges {
            if targetFPS >= (range.minFrameRate - eps), targetFPS <= (range.maxFrameRate + eps) {
                return (format, range)
            }
        }
    }

    return nil
}

@_cdecl("camera_start")
public func camera_start(width: Int32, height: Int32, fps: Double) -> Int32 {
    if gState.session != nil {
        return 0
    }

    guard let device = chooseDevice() else {
        return -1
    }

    guard let (format, fpsRange) = chooseFormat(
        device: device,
        targetWidth: width,
        targetHeight: height,
        targetFPS: fps
    ) else {
        return -2
    }

    do {
        try device.lockForConfiguration()
        device.activeFormat = format
        device.activeVideoMinFrameDuration = fpsRange.minFrameDuration
        device.activeVideoMaxFrameDuration = fpsRange.minFrameDuration
        device.unlockForConfiguration()
    } catch {
        return -3
    }

    let session = AVCaptureSession()
    session.beginConfiguration()

    guard let input = try? AVCaptureDeviceInput(device: device), session.canAddInput(input) else {
        return -4
    }
    session.addInput(input)

    let output = AVCaptureVideoDataOutput()
    output.alwaysDiscardsLateVideoFrames = true
    output.videoSettings = [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange
    ]

    guard session.canAddOutput(output) else {
        return -5
    }
    session.addOutput(output)

    let queue = DispatchQueue(label: "camera_bridge_queue")
    let delegate = FrameDelegate(state: gState)
    output.setSampleBufferDelegate(delegate, queue: queue)

    session.commitConfiguration()
    session.startRunning()

    gState.lock.lock()
    gState.session = session
    gState.output = output
    gState.input = input
    gState.delegate = delegate
    gState.queue = queue
    gState.lock.unlock()

    return 0
}

@_cdecl("camera_get_frame")
public func camera_get_frame(
    buffer: UnsafeMutablePointer<UInt8>?,
    maxBytes: Int32,
    outWidth: UnsafeMutablePointer<Int32>?,
    outHeight: UnsafeMutablePointer<Int32>?,
    outStride: UnsafeMutablePointer<Int32>?
) -> Int32 {
    guard let buffer = buffer else { return -1 }
    guard let outWidth = outWidth, let outHeight = outHeight, let outStride = outStride else { return -2 }

    gState.lock.lock()
    defer { gState.lock.unlock() }

    guard let frame = gState.latestFrame else {
        return 0
    }

    let needed = frame.count
    if needed > Int(maxBytes) {
        return -3
    }

    frame.copyBytes(to: buffer, count: needed)
    outWidth.pointee = Int32(gState.width)
    outHeight.pointee = Int32(gState.height)
    outStride.pointee = Int32(gState.stride)

    return Int32(needed)
}

@_cdecl("camera_stop")
public func camera_stop() {
    gState.lock.lock()
    let session = gState.session
    gState.session = nil
    gState.output = nil
    gState.input = nil
    gState.delegate = nil
    gState.queue = nil
    gState.latestFrame = nil
    gState.width = 0
    gState.height = 0
    gState.stride = 0
    gState.lock.unlock()

    session?.stopRunning()
}
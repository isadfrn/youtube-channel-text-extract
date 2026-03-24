import { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Button,
  Badge,
  Callout,
  Card,
  Checkbox,
  Flex,
  Heading,
  Select,
  Separator,
  Text,
  TextField,
} from "@radix-ui/themes";

// ── Log line colour ────────────────────────────────────────────────────────────

function getLineColor(line) {
  if (/^={3}/.test(line)) return "var(--accent-11)"; // step headers
  if (/^(error|failed|✗)/i.test(line)) return "var(--red-11)"; // errors
  if (/✓\s*done!?$/i.test(line) || /^✓/.test(line)) return "var(--green-11)"; // success
  if (/^output folder:/i.test(line)) return "var(--amber-11)"; // folder path
  if (/^warning/i.test(line)) return "var(--yellow-11)"; // warnings
  if (/^fetching|^loading whisper/i.test(line)) return "var(--gray-9)"; // dim status
  return "var(--gray-11)";
}

// ── Setup warning ─────────────────────────────────────────────────────────────

function SetupWarning({ checks }) {
  if (!checks) return null;
  const missing = [
    !checks.python && {
      label: "Python 3",
      detail: "Download from python.org and add to PATH",
    },
    !checks.ffmpeg && {
      label: "FFmpeg",
      detail: "Download from ffmpeg.org and add to PATH",
    },
  ].filter(Boolean);

  if (missing.length === 0) return null;

  return (
    <Callout.Root color="amber" variant="soft">
      <Callout.Text>
        <Flex direction="column" gap="1">
          <Text weight="medium">
            Missing {missing.length === 1 ? "dependency" : "dependencies"}{" "}
            detected
          </Text>
          {missing.map(({ label, detail }) => (
            <Text key={label} size="2">
              • <Text weight="medium">{label}</Text> — {detail}
            </Text>
          ))}
          <Text size="2" mt="1" color="gray">
            After installing Python, run{" "}
            <Text as="span" style={{ fontFamily: "monospace" }}>
              pip install -e .
            </Text>{" "}
            in the project root to set up ytextract.
          </Text>
        </Flex>
      </Callout.Text>
    </Callout.Root>
  );
}

// ── Status badge ───────────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  if (status === "running")
    return (
      <Badge color="blue" variant="soft" size="1">
        Running
      </Badge>
    );
  if (status === "done")
    return (
      <Badge color="green" variant="soft" size="1">
        Done ✓
      </Badge>
    );
  if (status === "error")
    return (
      <Badge color="red" variant="soft" size="1">
        Error
      </Badge>
    );
  if (status === "stopped")
    return (
      <Badge color="gray" variant="soft" size="1">
        Stopped
      </Badge>
    );
  return null;
}

// ── App ────────────────────────────────────────────────────────────────────────

export default function App() {
  // Setup check (Python + FFmpeg availability)
  const [setupChecks, setSetupChecks] = useState(null);

  // Form state
  const [url, setUrl] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [desktopPath, setDesktopPath] = useState("Desktop");
  const [format, setFormat] = useState("mp3");
  const [model, setModel] = useState("base");
  const [noArchive, setNoArchive] = useState(false);
  const [force, setForce] = useState(false);
  const [withTimestamps, setWithTimestamps] = useState(false);

  // Extraction state
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | running | done | error | stopped
  const [outputFolder, setOutputFolder] = useState("");

  // Refs
  const logRef = useRef(null);
  const isAtBottomRef = useRef(true);

  // ── Bootstrap ────────────────────────────────────────────────────────────────

  useEffect(() => {
    window.ytapi.getDesktopPath().then(setDesktopPath);
    window.ytapi.checkSetup().then(setSetupChecks);

    const cleanLog = window.ytapi.onLog((line) => {
      setLogs((prev) => [...prev, line]);
      if (/^output folder:/i.test(line)) {
        setOutputFolder(line.replace(/^output folder:\s*/i, "").trim());
      }
    });

    const cleanDone = window.ytapi.onDone((code) => {
      setStatus((prev) =>
        prev === "stopped" ? "stopped" : code === 0 ? "done" : "error",
      );
    });

    return () => {
      cleanLog();
      cleanDone();
    };
  }, []);

  // ── Auto-scroll ──────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!logRef.current || !isAtBottomRef.current) return;
    logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const handleScroll = useCallback(() => {
    if (!logRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    isAtBottomRef.current = scrollTop + clientHeight >= scrollHeight - 24;
  }, []);

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleBrowse = useCallback(async () => {
    const path = await window.ytapi.selectDirectory(outputDir || desktopPath);
    if (path) setOutputDir(path);
  }, [outputDir, desktopPath]);

  const handleStart = useCallback(() => {
    if (!url.trim() || status === "running") return;
    setLogs([]);
    setOutputFolder("");
    setStatus("running");
    isAtBottomRef.current = true;
    window.ytapi.startExtraction({
      channelUrl: url.trim(),
      outputDir: outputDir.trim() || null,
      format,
      model,
      noArchive,
      force,
      withTimestamps,
    });
  }, [url, outputDir, format, model, noArchive, force, withTimestamps, status]);

  const handleStop = useCallback(() => {
    window.ytapi.stopExtraction();
    setStatus("stopped");
    setLogs((prev) => [...prev, "Stopped by user."]);
  }, []);

  const handleOpenFolder = useCallback(() => {
    if (outputFolder) window.ytapi.openFolder(outputFolder);
  }, [outputFolder]);

  // ── Derived ──────────────────────────────────────────────────────────────────

  const isRunning = status === "running";
  const showLog = logs.length > 0;

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <Box
      style={{
        background: "var(--color-background)",
        minHeight: "100vh",
        padding: "28px 28px 36px",
      }}
    >
      <Flex
        direction="column"
        gap="4"
        style={{ maxWidth: 680, margin: "0 auto" }}
      >
        {/* ── Setup warning ── */}
        <SetupWarning checks={setupChecks} />

        {/* ── Header ── */}
        <Box pb="1">
          <Heading size="7" mb="1" style={{ letterSpacing: "-0.025em" }}>
            YouTube Channel Text Extract
          </Heading>
          <Text size="2" color="gray">
            Download and transcribe YouTube channel or video audio locally
          </Text>
        </Box>

        <Separator size="4" />

        {/* ── URL ── */}
        <Flex direction="column" gap="2">
          <Text as="label" size="2" weight="medium">
            YouTube channel or video URL
          </Text>
          <TextField.Root
            size="3"
            placeholder="https://www.youtube.com/@ChannelName   or   https://youtu.be/VIDEO_ID"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleStart()}
            disabled={isRunning}
          />
        </Flex>

        {/* ── Output directory ── */}
        <Flex direction="column" gap="2">
          <Text as="label" size="2" weight="medium">
            Output directory
          </Text>
          <Flex gap="2">
            <TextField.Root
              size="3"
              style={{ flex: 1 }}
              placeholder={`Default: ${desktopPath}`}
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              disabled={isRunning}
            />
            <Button
              size="3"
              variant="soft"
              onClick={handleBrowse}
              disabled={isRunning}
            >
              Browse…
            </Button>
          </Flex>
        </Flex>

        {/* ── Options ── */}
        <Card>
          <Flex direction="column" gap="4">
            {/* Selects row */}
            <Flex gap="6" align="start" wrap="wrap">
              <Flex direction="column" gap="1">
                <Text
                  size="1"
                  color="gray"
                  weight="medium"
                  style={{
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Audio format
                </Text>
                <Select.Root
                  size="2"
                  value={format}
                  onValueChange={setFormat}
                  disabled={isRunning}
                >
                  <Select.Trigger style={{ minWidth: 88 }} />
                  <Select.Content>
                    {["mp3", "m4a", "opus", "vorbis", "wav"].map((f) => (
                      <Select.Item key={f} value={f}>
                        {f}
                      </Select.Item>
                    ))}
                  </Select.Content>
                </Select.Root>
              </Flex>

              <Flex direction="column" gap="1">
                <Text
                  size="1"
                  color="gray"
                  weight="medium"
                  style={{
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Whisper model
                </Text>
                <Select.Root
                  size="2"
                  value={model}
                  onValueChange={setModel}
                  disabled={isRunning}
                >
                  <Select.Trigger style={{ minWidth: 230 }} />
                  <Select.Content>
                    <Select.Item value="tiny">
                      tiny — fastest, lowest accuracy
                    </Select.Item>
                    <Select.Item value="base">
                      base — fast, good accuracy
                    </Select.Item>
                    <Select.Item value="small">small — balanced</Select.Item>
                    <Select.Item value="medium">
                      medium — accurate, slower
                    </Select.Item>
                    <Select.Item value="large">
                      large — most accurate, slowest
                    </Select.Item>
                  </Select.Content>
                </Select.Root>
              </Flex>
            </Flex>

            {/* Checkboxes row */}
            <Flex gap="5" wrap="wrap">
              {[
                {
                  checked: noArchive,
                  onChange: setNoArchive,
                  label: "Re-download all",
                },
                {
                  checked: force,
                  onChange: setForce,
                  label: "Force re-transcribe",
                },
                {
                  checked: withTimestamps,
                  onChange: setWithTimestamps,
                  label: "Include timestamps (.srt)",
                },
              ].map(({ checked, onChange, label }) => (
                <Text key={label} as="label" size="2">
                  <Flex as="span" gap="2" align="center">
                    <Checkbox
                      checked={checked}
                      onCheckedChange={onChange}
                      disabled={isRunning}
                    />
                    {label}
                  </Flex>
                </Text>
              ))}
            </Flex>
          </Flex>
        </Card>

        {/* ── Action buttons ── */}
        <Flex gap="3">
          <Button
            size="3"
            style={{ flex: 1 }}
            disabled={isRunning || !url.trim()}
            onClick={handleStart}
          >
            {isRunning ? "Running…" : "Start Extraction"}
          </Button>
          <Button
            size="3"
            variant="soft"
            color="red"
            disabled={!isRunning}
            onClick={handleStop}
          >
            Stop
          </Button>
        </Flex>

        {/* ── Log panel ── */}
        {showLog && (
          <Card>
            <Flex direction="column" gap="3">
              {/* Panel header */}
              <Flex justify="between" align="center">
                <Flex gap="2" align="center">
                  <Text size="2" weight="medium">
                    Output
                  </Text>
                  <StatusBadge status={status} />
                </Flex>
                {outputFolder && !isRunning && (
                  <Button size="1" variant="ghost" onClick={handleOpenFolder}>
                    Open folder ↗
                  </Button>
                )}
              </Flex>

              {/* Terminal */}
              <Box
                ref={logRef}
                className="log-panel"
                onScroll={handleScroll}
                style={{
                  background: "var(--gray-2)",
                  borderRadius: "var(--radius-3)",
                  padding: "12px 14px",
                  height: 264,
                  overflowY: "auto",
                  fontFamily:
                    '"JetBrains Mono", "Cascadia Code", "Fira Code", Menlo, Monaco, Consolas, monospace',
                  fontSize: 12,
                  lineHeight: 1.75,
                }}
              >
                {logs.map((line, i) => (
                  <div
                    key={i}
                    className="log-line"
                    style={{ color: getLineColor(line) }}
                  >
                    {line}
                  </div>
                ))}
              </Box>

              {/* Output path subtitle */}
              {outputFolder && (
                <Text
                  size="1"
                  color="gray"
                  style={{
                    fontFamily: "monospace",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {outputFolder}
                </Text>
              )}
            </Flex>
          </Card>
        )}
      </Flex>
    </Box>
  );
}

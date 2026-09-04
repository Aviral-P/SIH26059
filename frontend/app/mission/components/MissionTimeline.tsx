import { Clock3 } from "lucide-react";
import { timeOptions } from "../constants";

interface MissionTimelineProps {
  selectedHour: number;
  onSelectHour: (hour: number) => void;
}

export default function MissionTimeline({
  selectedHour,
  onSelectHour,
}: MissionTimelineProps) {
  return (
    <div className="absolute bottom-14 left-1/2 z-20 w-[min(720px,80%)] -translate-x-1/2">
      <div className="border border-[#aeb7b6] bg-[#f7f8f6]/95 px-5 py-4 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock3 size={13} className="text-[#59666a]" />

            <span className="text-[9px] font-semibold tracking-[0.16em] text-[#59666a]">
              MISSION TIME
            </span>
          </div>

          <span className="font-mono text-[10px] text-[#59666a]">
            {selectedHour === 0
              ? "CURRENT"
              : selectedHour > 0
                ? `T + ${selectedHour}H`
                : `T ${selectedHour}H`}
          </span>
        </div>

        <div className="relative">
          <div className="absolute left-0 right-0 top-1.25 h-px bg-[#aeb7b6]" />

          <div className="relative flex justify-between">
            {timeOptions.map((option) => (
              <button
                key={option.hour}
                onClick={() => onSelectHour(option.hour)}
                className="group flex flex-col items-center"
              >
                <span
                  className={`h-2.75 w-2.75 border ${
                    selectedHour === option.hour
                      ? "border-[#365e72] bg-[#365e72]"
                      : "border-[#718084] bg-[#f7f8f6]"
                  }`}
                />

                <span
                  className={`mt-2 font-mono text-[9px] ${
                    selectedHour === option.hour
                      ? "font-semibold text-[#365e72]"
                      : "text-[#687579]"
                  }`}
                >
                  {option.label}
                </span>

                <span className="mt-1 text-[7px] tracking-wider text-[#899396]">
                  {option.type}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
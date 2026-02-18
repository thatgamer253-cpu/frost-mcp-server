// Ghidra Script: Decompile Crash-Critical Functions
// Traces memory leak, GPU crash, and texture streaming bugs to pseudo-C
// @category Analysis
// @author Kinetic Council

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import java.io.*;
import java.util.*;

public class ghidra_decompile_crashes extends GhidraScript {

    private DecompInterface decomp;

    @Override
    public void run() throws Exception {
        String outputPath = "C:\\Users\\thatg\\Desktop\\Modernize\\wow_crash_decompilation.txt";
        PrintWriter out = new PrintWriter(new FileWriter(outputPath));

        // Initialize decompiler
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        out.println("=== WoW.exe Crash Function Decompilation ===");
        out.println("Generated: " + new java.util.Date());
        out.println();

        // Target strings to trace - these are the crash vectors
        String[] crashStrings = {
                "Memory was allocated and never released",
                "Heap corrupt",
                "block header has been overwritten",
                "Access violation in Gx",
                "Failed to allocate MIP buffers",
                "Texture failure",
                "decompression failed",
                "out of memory",
                "D3DERR_OUTOFVIDEOMEMORY",
                "D3DERR_DEVICELOST",
                "unable to initialize heap",
                "unexpected heap error",
                "Fatal Condition",
                "Fatal Exception",
                "ObjectAlloc",
                "CDataAllocator",
                "stack overflow",
                "FSOUND_Init"
        };

        // Find all data items referencing these strings
        Set<Function> crashFunctions = new LinkedHashSet<>();
        DataIterator dataIter = currentProgram.getListing().getDefinedData(true);

        while (dataIter.hasNext()) {
            Data data = dataIter.next();
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                for (String target : crashStrings) {
                    if (val.contains(target)) {
                        out.println("--- String: " + val.substring(0, Math.min(val.length(), 80)));
                        out.println("    Address: " + data.getAddress());

                        // Find all references TO this string
                        Reference[] refs = getReferencesTo(data.getAddress());
                        out.println("    Referenced by " + refs.length + " locations:");

                        for (Reference ref : refs) {
                            Address fromAddr = ref.getFromAddress();
                            Function func = getFunctionContaining(fromAddr);
                            if (func != null) {
                                out.println("      -> " + func.getName() + " @ " + func.getEntryPoint() +
                                        " (size: " + func.getBody().getNumAddresses() + " bytes)");
                                crashFunctions.add(func);
                            } else {
                                out.println("      -> [no function] @ " + fromAddr);
                            }
                        }
                        out.println();
                        break;
                    }
                }
            }
        }

        // Decompile each crash-related function
        out.println("\n=== DECOMPILED CRASH FUNCTIONS ===\n");
        int decompCount = 0;
        int maxDecomp = 30; // Limit to top 30 to keep output manageable

        for (Function func : crashFunctions) {
            if (decompCount >= maxDecomp)
                break;

            out.println("╔══════════════════════════════════════════════════════════");
            out.println("║ Function: " + func.getName());
            out.println("║ Address:  " + func.getEntryPoint());
            out.println("║ Size:     " + func.getBody().getNumAddresses() + " bytes");
            out.println("╚══════════════════════════════════════════════════════════");

            // Get callers (who calls this crash function?)
            Set<Function> callers = func.getCallingFunctions(monitor);
            if (!callers.isEmpty()) {
                out.println("  CALLERS (who triggers this crash path):");
                int callerCount = 0;
                for (Function caller : callers) {
                    out.println("    <- " + caller.getName() + " @ " + caller.getEntryPoint());
                    callerCount++;
                    if (callerCount >= 10) {
                        out.println("    ... and " + (callers.size() - 10) + " more callers");
                        break;
                    }
                }
            }

            // Get callees (what does this function call?)
            Set<Function> callees = func.getCalledFunctions(monitor);
            if (!callees.isEmpty()) {
                out.println("  CALLEES (what this function invokes):");
                int calleeCount = 0;
                for (Function callee : callees) {
                    out.println("    -> " + callee.getName() + " @ " + callee.getEntryPoint());
                    calleeCount++;
                    if (calleeCount >= 10) {
                        out.println("    ... and " + (callees.size() - 10) + " more callees");
                        break;
                    }
                }
            }

            // Decompile to pseudo-C
            out.println("\n  DECOMPILED CODE:");
            try {
                DecompileResults results = decomp.decompileFunction(func, 30, monitor);
                if (results.decompileCompleted()) {
                    String code = results.getDecompiledFunction().getC();
                    // Limit output per function
                    if (code.length() > 3000) {
                        out.println(code.substring(0, 3000));
                        out.println("  ... [truncated, " + code.length() + " chars total]");
                    } else {
                        out.println(code);
                    }
                } else {
                    out.println("  [Decompilation failed: " + results.getErrorMessage() + "]");
                }
            } catch (Exception e) {
                out.println("  [Error: " + e.getMessage() + "]");
            }

            out.println("\n");
            decompCount++;
        }

        out.println("Total crash functions decompiled: " + decompCount);
        out.println("\n=== DECOMPILATION COMPLETE ===");
        out.close();
        decomp.dispose();

        println("Crash decompilation saved to: " + outputPath);
    }
}

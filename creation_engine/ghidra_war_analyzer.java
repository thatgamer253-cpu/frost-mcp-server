// Ghidra Script: WAR-64.exe Crash & Performance Analysis
// For Return of Reckoning (Warhammer Online: Age of Reckoning)
// @category Analysis
// @author Kinetic Council

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.address.*;
import ghidra.app.decompiler.*;
import java.io.*;
import java.util.*;

public class ghidra_war_analyzer extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputPath = "C:\\Users\\thatg\\Desktop\\Modernize\\war_analysis_report.txt";
        PrintWriter out = new PrintWriter(new FileWriter(outputPath));

        out.println("=== WAR-64.exe (Return of Reckoning) Analysis Report ===");
        out.println("Generated: " + new java.util.Date());
        out.println("Binary: " + currentProgram.getName());
        out.println("Architecture: " + currentProgram.getLanguage().getProcessor());
        out.println();

        // 1. Count total functions
        FunctionManager fm = currentProgram.getFunctionManager();
        int totalFunctions = 0;
        FunctionIterator allFuncs = fm.getFunctions(true);
        while (allFuncs.hasNext()) {
            allFuncs.next();
            totalFunctions++;
        }
        out.println("Total Functions Found: " + totalFunctions);
        out.println();

        // 2. Find crash/error strings
        out.println("=== CRASH/ERROR STRINGS ===");
        String[] crashPatterns = {
                "Error", "FATAL", "crash", "assert", "failed",
                "exception", "invalid", "corrupt", "overflow",
                "out of memory", "null", "access violation",
                "heap", "alloc", "leak", "siege", "Gamebryo",
                "render", "draw", "texture", "shader", "mesh",
                "D3D", "Direct3D", "DXGI", "device lost",
                "disconnect", "timeout", "socket", "network"
        };

        int errorStrings = 0;
        DataIterator dataIter = currentProgram.getListing().getDefinedData(true);
        while (dataIter.hasNext()) {
            Data data = dataIter.next();
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                for (String pattern : crashPatterns) {
                    if (val.toLowerCase().contains(pattern.toLowerCase())) {
                        out.println("  [" + data.getAddress() + "] " +
                                val.substring(0, Math.min(val.length(), 120)));
                        errorStrings++;
                        break;
                    }
                }
            }
        }
        out.println("Total error-related strings: " + errorStrings);
        out.println();

        // 3. Critical API references
        out.println("=== CRITICAL API REFERENCES ===");
        String[] criticalAPIs = {
                "ExitProcess", "TerminateProcess", "RaiseException",
                "SetUnhandledExceptionFilter", "HeapAlloc", "HeapFree",
                "VirtualAlloc", "VirtualFree", "CreateThread",
                "Direct3DCreate9", "CreateDevice"
        };

        SymbolTable st = currentProgram.getSymbolTable();
        for (String api : criticalAPIs) {
            SymbolIterator symbols = st.getSymbols(api);
            while (symbols.hasNext()) {
                Symbol sym = symbols.next();
                Reference[] refs = getReferencesTo(sym.getAddress());
                out.println("  " + api + " @ " + sym.getAddress() +
                        " (referenced " + refs.length + " times)");
            }
        }
        out.println();

        // 4. Top 50 largest functions
        out.println("=== TOP 50 LARGEST FUNCTIONS ===");
        List<String> largeFuncs = new ArrayList<>();
        FunctionIterator fi = fm.getFunctions(true);
        while (fi.hasNext()) {
            Function f = fi.next();
            long size = f.getBody().getNumAddresses();
            if (size > 500) {
                largeFuncs.add(String.format("  [%s] %s (%d bytes)",
                        f.getEntryPoint(), f.getName(), size));
            }
        }
        Collections.sort(largeFuncs, (a, b) -> {
            int sizeA = Integer.parseInt(a.replaceAll(".*\\((\\d+) bytes\\)", "$1"));
            int sizeB = Integer.parseInt(b.replaceAll(".*\\((\\d+) bytes\\)", "$1"));
            return sizeB - sizeA;
        });
        for (int i = 0; i < Math.min(50, largeFuncs.size()); i++) {
            out.println(largeFuncs.get(i));
        }
        out.println();

        // 5. Named functions (Gamebryo engine often preserves names)
        out.println("=== NAMED/SYMBOLIC FUNCTIONS ===");
        fi = fm.getFunctions(true);
        int namedCount = 0;
        while (fi.hasNext()) {
            Function f = fi.next();
            String name = f.getName();
            if (!name.startsWith("FUN_") && !name.startsWith("_") &&
                    !name.equals("entry") && name.length() > 3) {
                out.println("  [" + f.getEntryPoint() + "] " + name);
                namedCount++;
                if (namedCount >= 200) {
                    out.println("  ... (showing first 200 of named functions)");
                    break;
                }
            }
        }
        out.println("Named functions found: " + namedCount);
        out.println();

        // 6. Find rendering-related strings
        out.println("=== RENDERING ENGINE STRINGS ===");
        dataIter = currentProgram.getListing().getDefinedData(true);
        while (dataIter.hasNext()) {
            Data data = dataIter.next();
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                String lower = val.toLowerCase();
                if (lower.contains("render") || lower.contains("shader") ||
                        lower.contains("vertex") || lower.contains("pixel") ||
                        lower.contains("d3d") || lower.contains("draw call") ||
                        lower.contains("batch") || lower.contains("frustum") ||
                        lower.contains("occlusion") || lower.contains("shadow")) {
                    out.println("  [" + data.getAddress() + "] " +
                            val.substring(0, Math.min(val.length(), 120)));
                }
            }
        }
        out.println();

        out.println("=== ANALYSIS COMPLETE ===");
        out.close();

        println("WAR Analysis Report saved to: " + outputPath);
    }
}
